# -*- coding: utf-8 -*-
"""
===================================
A주 관심 종목 지능형 분석 시스템 - 핵심 분석 파이프라인
===================================

역할：
1. 전체 분석 프로세스 관리
2. 데이터 수집, 저장, 검색, 분석, 알림 모듈 조율
3. 동시성 제어 및 예외 처리 구현
4. 주식 분석 핵심 기능 제공
"""

import logging
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd

from src.config import get_config, Config
from src.storage import get_db
from data_provider import DataFetcherManager
from data_provider.realtime_types import ChipDistribution
from src.analyzer import GeminiAnalyzer, AnalysisResult, STOCK_NAME_MAP
from src.notification import NotificationService, NotificationChannel
from src.search_service import SearchService
from src.enums import ReportType
from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult
from src.core.trading_calendar import get_market_for_stock, is_market_open
from bot.models import BotMessage


logger = logging.getLogger(__name__)


class StockAnalysisPipeline:
    """
    주식 분석 메인 프로세스 스케줄러
    
    역할：
    1. 전체 분석 프로세스 관리
    2. 데이터 수집, 저장, 검색, 분석, 알림 모듈 조율
    3. 동시성 제어 및 예외 처리 구현
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        max_workers: Optional[int] = None,
        source_message: Optional[BotMessage] = None,
        query_id: Optional[str] = None,
        query_source: Optional[str] = None,
        save_context_snapshot: Optional[bool] = None
    ):
        """
        스케줄러 초기화
        
        Args:
            config: 설정 객체（선택, 기본값은 전역 설정 사용）
            max_workers: 최대 동시 스레드 수（선택, 기본값은 설정에서 읽음）
        """
        self.config = config or get_config()
        self.max_workers = max_workers or self.config.max_workers
        self.source_message = source_message
        self.query_id = query_id
        self.query_source = self._resolve_query_source(query_source)
        self.save_context_snapshot = (
            self.config.save_context_snapshot if save_context_snapshot is None else save_context_snapshot
        )
        
        # 각 모듈 초기화
        self.db = get_db()
        self.fetcher_manager = DataFetcherManager()
        # akshare_fetcher를 별도로 생성하지 않고 fetcher_manager로 통합하여 향상된 데이터 조회
        self.trend_analyzer = StockTrendAnalyzer()  # 추세 분석기
        self.analyzer = GeminiAnalyzer()
        self.notifier = NotificationService(source_message=source_message)
        
        # 검색 서비스 초기화
        self.search_service = SearchService(
            bocha_keys=self.config.bocha_api_keys,
            tavily_keys=self.config.tavily_api_keys,
            brave_keys=self.config.brave_api_keys,
            serpapi_keys=self.config.serpapi_keys,
            news_max_age_days=self.config.news_max_age_days,
        )
        
        logger.info(f"스케줄러 초기화 완료, 최대 동시 처리 수: {self.max_workers}")
        logger.info("추세 분석기 활성화 (MA5>MA10>MA20 강세 판단)")
        # 실시간 시세/주주 구조 설정 상태 출력
        if self.config.enable_realtime_quote:
            logger.info(f"실시간 시세 활성화 (우선순위: {self.config.realtime_source_priority})")
        else:
            logger.info("실시간 시세 비활성화, 과거 종가 사용")
        if self.config.enable_chip_distribution:
            logger.info("주주 구조 분석 활성화")
        else:
            logger.info("주주 구조 분석 비활성화")
        if self.search_service.is_available:
            logger.info("검색 서비스 활성화 (Tavily/SerpAPI)")
        else:
            logger.warning("검색 서비스 비활성화（API 키 미설정）")
    
    def fetch_and_save_stock_data(
        self, 
        code: str,
        force_refresh: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        단일 종목 데이터 조회 및 저장
        
        체크포인트 재시작 로직：
        1. 데이터베이스에 오늘 데이터가 있는지 확인
        2. 있고 강제 새로 고침이 아니면 네트워크 요청 건너뜀
        3. 그렇지 않으면 데이터 소스에서 조회 및 저장
        
        Args:
            code: 종목 코드
            force_refresh: 강제 새로 고침 여부（로컬 캐시 무시）
            
        Returns:
            Tuple[성공 여부, 오류 메시지]
        """
        try:
            # 먼저 종목명 조회
            stock_name = self.fetcher_manager.get_stock_name(code)

            today = date.today()
            # 주의: 자연일 date.today()로 “체크포인트 재시작” 판단.
            # 주말/공휴일/비거래일에 실행하거나 서버 시간대가 중국이 아닌 경우:
            # - DB에 최신 거래일 데이터가 있어도 반복 조회 가능（has_today_data가 False 반환）
            # - 또는 날짜 전환/시간대 오프셋 시 “오늘 데이터 있음” 오판 가능
            # 현재 이 동작은 유지（요구사항대로 로직 미변경）, 더 엄밀하게 하려면 “최신 거래일/데이터 소스 최신 날짜” 판단으로 변경 가능.
            
            # 체크포인트 재시작 확인: 오늘 데이터가 이미 있으면 건너뜀
            if not force_refresh and self.db.has_today_data(code, today):
                logger.info(f"{stock_name}({code}) 오늘 데이터가 이미 있음, 조회 건너뜀（체크포인트 재시작）")
                return True, None

            # 데이터 소스에서 데이터 조회
            logger.info(f"{stock_name}({code}) 데이터 소스에서 데이터 조회 시작...")
            df, source_name = self.fetcher_manager.get_daily_data(code, days=30)

            if df is None or df.empty:
                return False, "조회된 데이터 없음"

            # 데이터베이스에 저장
            saved_count = self.db.save_daily_data(df, code, source_name)
            logger.info(f"{stock_name}({code}) 데이터 저장 완료（출처: {source_name}, 신규 {saved_count}건）")

            return True, None

        except Exception as e:
            error_msg = f"데이터 조회/저장 실패: {str(e)}"
            logger.error(f"{stock_name}({code}) {error_msg}")
            return False, error_msg
    
    def analyze_stock(self, code: str, report_type: ReportType, query_id: str) -> Optional[AnalysisResult]:
        """
        단일 종목 분석（강화 버전: 거래량 비율, 회전율, 주주 구조 분석, 다차원 정보 포함）
        
        흐름：
        1. 실시간 시세 조회（거래량 비율, 회전율）- DataFetcherManager를 통한 자동 장애 전환
        2. 주주 구조 조회 - DataFetcherManager 서킷 브레이커 보호
        3. 추세 분석 실행（매매 원칙 기반）
        4. 다차원 정보 검색（최신 뉴스+리스크 점검+실적 전망）
        5. 데이터베이스에서 분석 컨텍스트 조회
        6. AI 종합 분석 호출
        
        Args:
            query_id: 쿼리 연결 id
            code: 종목 코드
            report_type: 보고서 유형
            
        Returns:
            AnalysisResult 또는 None（분석 실패 시）
        """
        try:
            # 종목명 조회（실시간 시세에서 실제 이름 우선 조회）
            stock_name = self.fetcher_manager.get_stock_name(code)

            # Step 1: 실시간 시세 조회（거래량 비율, 회전율 등）- 통합 진입점, 자동 장애 전환
            realtime_quote = None
            try:
                realtime_quote = self.fetcher_manager.get_realtime_quote(code)
                if realtime_quote:
                    # 실시간 시세에서 반환된 실제 종목명 사용
                    if realtime_quote.name:
                        stock_name = realtime_quote.name
                    # 데이터 소스 필드 호환（일부 소스는 volume_ratio가 없을 수 있음）
                    volume_ratio = getattr(realtime_quote, 'volume_ratio', None)
                    turnover_rate = getattr(realtime_quote, 'turnover_rate', None)
                    logger.info(f"{stock_name}({code}) 실시간 시세: 가격={realtime_quote.price}, "
                              f"거래량비율={volume_ratio}, 회전율={turnover_rate}% "
                              f"(출처: {realtime_quote.source.value if hasattr(realtime_quote, 'source') else 'unknown'})")
                else:
                    logger.info(f"{stock_name}({code}) 실시간 시세 조회 실패 또는 비활성화, 과거 데이터로 분석 진행")
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 실시간 시세 조회 실패: {e}")

            # 그래도 이름이 없으면 코드를 이름으로 사용
            if not stock_name:
                stock_name = f'종목{code}'

            # Step 2: 주주 구조 조회 - 통합 진입점, 서킷 브레이커 보호
            chip_data = None
            try:
                chip_data = self.fetcher_manager.get_chip_distribution(code)
                if chip_data:
                    logger.info(f"{stock_name}({code}) 주주 구조: 수익 비율={chip_data.profit_ratio:.1%}, "
                              f"90% 집중도={chip_data.concentration_90:.2%}")
                else:
                    logger.debug(f"{stock_name}({code}) 주주 구조 조회 실패 또는 비활성화")
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 주주 구조 조회 실패: {e}")

            # If agent mode is enabled, or specific agent skills are configured, use the Agent analysis pipeline
            use_agent = getattr(self.config, 'agent_mode', False)
            if not use_agent:
                # Auto-enable agent mode when specific skills are configured (e.g., scheduled task with strategy)
                configured_skills = getattr(self.config, 'agent_skills', [])
                if configured_skills and configured_skills != ['all']:
                    use_agent = True
                    logger.info(f"{stock_name}({code}) Auto-enabled agent mode due to configured skills: {configured_skills}")

            if use_agent:
                logger.info(f"{stock_name}({code}) Agent 모드로 분석 활성화")
                return self._analyze_with_agent(code, report_type, query_id, stock_name, realtime_quote, chip_data)
            
            # Step 3: 추세 분석（매매 원칙 기반）
            trend_result: Optional[TrendAnalysisResult] = None
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=89)  # ~60 trading days for MA60
                historical_bars = self.db.get_data_range(code, start_date, end_date)
                if historical_bars:
                    df = pd.DataFrame([bar.to_dict() for bar in historical_bars])
                    # Issue #234: Augment with realtime for intraday MA calculation
                    if self.config.enable_realtime_quote and realtime_quote:
                        df = self._augment_historical_with_realtime(df, realtime_quote, code)
                    trend_result = self.trend_analyzer.analyze(df, code)
                    logger.info(f"{stock_name}({code}) 추세 분석: {trend_result.trend_status.value}, "
                              f"매수 신호={trend_result.buy_signal.value}, 점수={trend_result.signal_score}")
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 추세 분석 실패: {e}", exc_info=True)

            # Step 4: 다차원 정보 검색（최신 뉴스+리스크 점검+실적 전망）
            news_context = None
            if self.search_service.is_available:
                logger.info(f"{stock_name}({code}) 다차원 정보 검색 시작...")

                # 다차원 검색 사용（최대 5회 검색）
                intel_results = self.search_service.search_comprehensive_intel(
                    stock_code=code,
                    stock_name=stock_name,
                    max_searches=5
                )

                # 정보 보고서 포맷 변환
                if intel_results:
                    news_context = self.search_service.format_intel_report(intel_results, stock_name)
                    total_results = sum(
                        len(r.results) for r in intel_results.values() if r.success
                    )
                    logger.info(f"{stock_name}({code}) 정보 검색 완료: 총 {total_results}건 결과")
                    logger.debug(f"{stock_name}({code}) 정보 검색 결과:\n{news_context}")

                    # 뉴스 정보를 DB에 저장（이후 복기 및 조회 용도）
                    try:
                        query_context = self._build_query_context(query_id=query_id)
                        for dim_name, response in intel_results.items():
                            if response and response.success and response.results:
                                self.db.save_news_intel(
                                    code=code,
                                    name=stock_name,
                                    dimension=dim_name,
                                    query=response.query,
                                    response=response,
                                    query_context=query_context
                                )
                    except Exception as e:
                        logger.warning(f"{stock_name}({code}) 뉴스 정보 저장 실패: {e}")
            else:
                logger.info(f"{stock_name}({code}) 검색 서비스 사용 불가, 정보 검색 건너뜀")

            # Step 5: 분석 컨텍스트 조회（기술적 데이터）
            context = self.db.get_analysis_context(code)

            if context is None:
                logger.warning(f"{stock_name}({code}) 과거 시세 데이터 조회 불가, 뉴스 및 실시간 시세만으로 분석")
                context = {
                    'code': code,
                    'stock_name': stock_name,
                    'date': date.today().isoformat(),
                    'data_missing': True,
                    'today': {},
                    'yesterday': {}
                }
            
            # Step 6: 컨텍스트 데이터 강화（실시간 시세, 주주 구조, 추세 분석 결과, 종목명 추가）
            enhanced_context = self._enhance_context(
                context, 
                realtime_quote, 
                chip_data, 
                trend_result,
                stock_name  # 종목명 전달
            )
            
            # Step 7: AI 분석 호출（강화된 컨텍스트 및 뉴스 전달）
            result = self.analyzer.analyze(enhanced_context, news_context=news_context)

            # Step 7.5: 분석 시 가격 정보를 result에 채워넣기
            if result:
                realtime_data = enhanced_context.get('realtime', {})
                result.current_price = realtime_data.get('price')
                result.change_pct = realtime_data.get('change_pct')

            # Step 8: 분석 이력 저장
            if result:
                try:
                    context_snapshot = self._build_context_snapshot(
                        enhanced_context=enhanced_context,
                        news_content=news_context,
                        realtime_quote=realtime_quote,
                        chip_data=chip_data
                    )
                    self.db.save_analysis_history(
                        result=result,
                        query_id=query_id,
                        report_type=report_type.value,
                        news_content=news_context,
                        context_snapshot=context_snapshot,
                        save_snapshot=self.save_context_snapshot
                    )
                except Exception as e:
                    logger.warning(f"{stock_name}({code}) 분석 이력 저장 실패: {e}")

            return result

        except Exception as e:
            logger.error(f"{stock_name}({code}) 분석 실패: {e}")
            logger.exception(f"{stock_name}({code}) 상세 오류 정보:")
            return None
    
    def _enhance_context(
        self,
        context: Dict[str, Any],
        realtime_quote,
        chip_data: Optional[ChipDistribution],
        trend_result: Optional[TrendAnalysisResult],
        stock_name: str = ""
    ) -> Dict[str, Any]:
        """
        분석 컨텍스트 강화
        
        실시간 시세, 주주 구조, 추세 분석 결과, 종목명을 컨텍스트에 추가
        
        Args:
            context: 원본 컨텍스트
            realtime_quote: 실시간 시세 데이터（UnifiedRealtimeQuote 또는 None）
            chip_data: 주주 구조 데이터
            trend_result: 추세 분석 결과
            stock_name: 종목명
            
        Returns:
            강화된 컨텍스트
        """
        enhanced = context.copy()
        
        # 종목명 추가
        if stock_name:
            enhanced['stock_name'] = stock_name
        elif realtime_quote and getattr(realtime_quote, 'name', None):
            enhanced['stock_name'] = realtime_quote.name
        
        # 실시간 시세 추가（데이터 소스 필드 차이 호환）
        if realtime_quote:
            # getattr로 안전하게 필드 조회, 없는 필드는 None 또는 기본값 반환
            volume_ratio = getattr(realtime_quote, 'volume_ratio', None)
            enhanced['realtime'] = {
                'name': getattr(realtime_quote, 'name', ''),
                'price': getattr(realtime_quote, 'price', None),
                'change_pct': getattr(realtime_quote, 'change_pct', None),
                'volume_ratio': volume_ratio,
                'volume_ratio_desc': self._describe_volume_ratio(volume_ratio) if volume_ratio else '데이터 없음',
                'turnover_rate': getattr(realtime_quote, 'turnover_rate', None),
                'pe_ratio': getattr(realtime_quote, 'pe_ratio', None),
                'pb_ratio': getattr(realtime_quote, 'pb_ratio', None),
                'total_mv': getattr(realtime_quote, 'total_mv', None),
                'circ_mv': getattr(realtime_quote, 'circ_mv', None),
                'change_60d': getattr(realtime_quote, 'change_60d', None),
                'source': getattr(realtime_quote, 'source', None),
            }
            # None 값 제거로 컨텍스트 크기 줄이기
            enhanced['realtime'] = {k: v for k, v in enhanced['realtime'].items() if v is not None}
        
        # 주주 구조 추가
        if chip_data:
            current_price = getattr(realtime_quote, 'price', 0) if realtime_quote else 0
            enhanced['chip'] = {
                'profit_ratio': chip_data.profit_ratio,
                'avg_cost': chip_data.avg_cost,
                'concentration_90': chip_data.concentration_90,
                'concentration_70': chip_data.concentration_70,
                'chip_status': chip_data.get_chip_status(current_price or 0),
            }
        
        # 추세 분석 결과 추가
        if trend_result:
            enhanced['trend_analysis'] = {
                'trend_status': trend_result.trend_status.value,
                'ma_alignment': trend_result.ma_alignment,
                'trend_strength': trend_result.trend_strength,
                'bias_ma5': trend_result.bias_ma5,
                'bias_ma10': trend_result.bias_ma10,
                'volume_status': trend_result.volume_status.value,
                'volume_trend': trend_result.volume_trend,
                'buy_signal': trend_result.buy_signal.value,
                'signal_score': trend_result.signal_score,
                'signal_reasons': trend_result.signal_reasons,
                'risk_factors': trend_result.risk_factors,
            }

        # Issue #234: Override today with realtime OHLC + trend MA for intraday analysis
        # Guard: trend_result.ma5 > 0 ensures MA calculation succeeded (data sufficient)
        if realtime_quote and trend_result and trend_result.ma5 > 0:
            price = getattr(realtime_quote, 'price', None)
            if price is not None and price > 0:
                yesterday_close = None
                if enhanced.get('yesterday') and isinstance(enhanced['yesterday'], dict):
                    yesterday_close = enhanced['yesterday'].get('close')
                orig_today = enhanced.get('today') or {}
                open_p = getattr(realtime_quote, 'open_price', None) or getattr(
                    realtime_quote, 'pre_close', None
                ) or yesterday_close or orig_today.get('open') or price
                high_p = getattr(realtime_quote, 'high', None) or price
                low_p = getattr(realtime_quote, 'low', None) or price
                vol = getattr(realtime_quote, 'volume', None)
                amt = getattr(realtime_quote, 'amount', None)
                pct = getattr(realtime_quote, 'change_pct', None)
                realtime_today = {
                    'close': price,
                    'open': open_p,
                    'high': high_p,
                    'low': low_p,
                    'ma5': trend_result.ma5,
                    'ma10': trend_result.ma10,
                    'ma20': trend_result.ma20,
                }
                if vol is not None:
                    realtime_today['volume'] = vol
                if amt is not None:
                    realtime_today['amount'] = amt
                if pct is not None:
                    realtime_today['pct_chg'] = pct
                for k, v in orig_today.items():
                    if k not in realtime_today and v is not None:
                        realtime_today[k] = v
                enhanced['today'] = realtime_today
                enhanced['ma_status'] = self._compute_ma_status(
                    price, trend_result.ma5, trend_result.ma10, trend_result.ma20
                )
                enhanced['date'] = date.today().isoformat()
                if yesterday_close is not None:
                    try:
                        yc = float(yesterday_close)
                        if yc > 0:
                            enhanced['price_change_ratio'] = round(
                                (price - yc) / yc * 100, 2
                            )
                    except (TypeError, ValueError):
                        pass
                if vol is not None and enhanced.get('yesterday'):
                    yest_vol = enhanced['yesterday'].get('volume') if isinstance(
                        enhanced['yesterday'], dict
                    ) else None
                    if yest_vol is not None:
                        try:
                            yv = float(yest_vol)
                            if yv > 0:
                                enhanced['volume_change_ratio'] = round(
                                    float(vol) / yv, 2
                                )
                        except (TypeError, ValueError):
                            pass

        # ETF/index flag for analyzer prompt (Fixes #274)
        enhanced['is_index_etf'] = SearchService.is_index_or_etf(
            context.get('code', ''), enhanced.get('stock_name', stock_name)
        )

        return enhanced

    def _analyze_with_agent(
        self, 
        code: str, 
        report_type: ReportType, 
        query_id: str,
        stock_name: str,
        realtime_quote: Any,
        chip_data: Optional[ChipDistribution]
    ) -> Optional[AnalysisResult]:
        """
        Agent 모드로 단일 종목 분석.
        """
        try:
            from src.agent.factory import build_agent_executor

            # Build executor from shared factory (ToolRegistry and SkillManager prototype are cached)
            executor = build_agent_executor(self.config, getattr(self.config, 'agent_skills', None) or None)

            # Build initial context to avoid redundant tool calls
            initial_context = {
                "stock_code": code,
                "stock_name": stock_name,
                "report_type": report_type.value,
            }
            
            if realtime_quote:
                initial_context["realtime_quote"] = self._safe_to_dict(realtime_quote)
            if chip_data:
                initial_context["chip_distribution"] = self._safe_to_dict(chip_data)

            # Agent 실행
            message = f"종목 {code} ({stock_name})를 분석하고 의사결정 대시보드 보고서를 생성해 주세요."
            agent_result = executor.run(message, context=initial_context)

            # AnalysisResult로 변환
            result = self._agent_result_to_analysis_result(agent_result, code, stock_name, report_type, query_id)
            resolved_stock_name = result.name if result and result.name else stock_name

            # 뉴스 정보를 DB에 저장（Agent 도구 결과는 LLM 컨텍스트 용도로만 사용, 미지속화, Fixes #396）
            # search_stock_news 사용（Agent 도구 호출 로직과 일치）, API 1회 호출, 추가 지연 없음
            if self.search_service.is_available:
                try:
                    news_response = self.search_service.search_stock_news(
                        stock_code=code,
                        stock_name=resolved_stock_name,
                        max_results=5
                    )
                    if news_response.success and news_response.results:
                        query_context = self._build_query_context(query_id=query_id)
                        self.db.save_news_intel(
                            code=code,
                            name=resolved_stock_name,
                            dimension="latest_news",
                            query=news_response.query,
                            response=news_response,
                            query_context=query_context
                        )
                        logger.info(f"[{code}] Agent 모드: 뉴스 정보 저장 완료 {len(news_response.results)}건")
                except Exception as e:
                    logger.warning(f"[{code}] Agent 모드 뉴스 정보 저장 실패: {e}")

            # 분석 이력 저장
            if result:
                try:
                    initial_context["stock_name"] = resolved_stock_name
                    self.db.save_analysis_history(
                        result=result,
                        query_id=query_id,
                        report_type=report_type.value,
                        news_content=None,
                        context_snapshot=initial_context,
                        save_snapshot=self.save_context_snapshot
                    )
                except Exception as e:
                    logger.warning(f"[{code}] Agent 분석 이력 저장 실패: {e}")

            return result

        except Exception as e:
            logger.error(f"[{code}] Agent 분석 실패: {e}")
            logger.exception(f"[{code}] Agent 상세 오류 정보:")
            return None

    def _agent_result_to_analysis_result(
        self, agent_result, code: str, stock_name: str, report_type: ReportType, query_id: str
    ) -> AnalysisResult:
        """
        AgentResult를 AnalysisResult로 변환.
        """
        result = AnalysisResult(
            code=code,
            name=stock_name,
            sentiment_score=50,
            trend_prediction="未知",
            operation_advice="观望",
            success=agent_result.success,
            error_message=agent_result.error if not agent_result.success else None,
            data_sources=f"agent:{agent_result.provider}",
            model_used=agent_result.model or None,
        )

        if agent_result.success and agent_result.dashboard:
            dash = agent_result.dashboard
            ai_stock_name = str(dash.get("stock_name", "")).strip()
            if ai_stock_name and self._is_placeholder_stock_name(stock_name, code):
                result.name = ai_stock_name
            result.sentiment_score = self._safe_int(dash.get("sentiment_score"), 50)
            result.trend_prediction = dash.get("trend_prediction", "未知")
            result.operation_advice = dash.get("operation_advice", "观望")
            result.decision_type = dash.get("decision_type", "hold")
            result.analysis_summary = dash.get("analysis_summary", "")
            # The AI returns a top-level dict that contains a nested 'dashboard' sub-key
            # with core_conclusion / battle_plan / intelligence.  AnalysisResult's helper
            # methods (get_sniper_points, get_core_conclusion, etc.) expect that inner
            # structure, so we unwrap it here.
            result.dashboard = dash.get("dashboard") or dash
        else:
            result.sentiment_score = 50
            result.operation_advice = "观望"
            if not result.error_message:
                result.error_message = "Agent가 유효한 의사결정 대시보드를 생성하지 못함"

        return result

    @staticmethod
    def _is_placeholder_stock_name(name: str, code: str) -> bool:
        """Return True when the stock name is missing or placeholder-like."""
        if not name:
            return True
        normalized = str(name).strip()
        if not normalized:
            return True
        if normalized == code:
            return True
        if normalized.startswith("종목") or normalized.startswith("股票"):
            return True
        if "Unknown" in normalized:
            return True
        return False

    @staticmethod
    def _safe_int(value: Any, default: int = 50) -> int:
        """값을 안전하게 정수로 변환."""
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            import re
            match = re.search(r'-?\d+', value)
            if match:
                return int(match.group())
        return default
    
    def _describe_volume_ratio(self, volume_ratio: float) -> str:
        """
        거래량 비율 설명
        
        거래량 비율 = 현재 거래량 / 과거 5일 평균 거래량
        """
        if volume_ratio < 0.5:
            return "극도로 감소"
        elif volume_ratio < 0.8:
            return "뚜렷이 감소"
        elif volume_ratio < 1.2:
            return "정상"
        elif volume_ratio < 2.0:
            return "완만한 거래량 증가"
        elif volume_ratio < 3.0:
            return "뚜렷이 증가"
        else:
            return "대량"

    @staticmethod
    def _compute_ma_status(close: float, ma5: float, ma10: float, ma20: float) -> str:
        """
        Compute MA alignment status from price and MA values.
        Logic mirrors storage._analyze_ma_status (Issue #234).
        """
        close = close or 0
        ma5 = ma5 or 0
        ma10 = ma10 or 0
        ma20 = ma20 or 0
        if close > ma5 > ma10 > ma20 > 0:
            return "강세 정렬 📈"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "약세 정렬 📉"
        elif close > ma5 and ma5 > ma10:
            return "단기 향상 🔼"
        elif close < ma5 and ma5 < ma10:
            return "단기 약화 🔽"
        else:
            return "횡보 조정 ↔️"

    def _augment_historical_with_realtime(
        self, df: pd.DataFrame, realtime_quote: Any, code: str
    ) -> pd.DataFrame:
        """
        Augment historical OHLCV with today's realtime quote for intraday MA calculation.
        Issue #234: Use realtime price instead of yesterday's close for technical indicators.
        """
        if df is None or df.empty or 'close' not in df.columns:
            return df
        if realtime_quote is None:
            return df
        price = getattr(realtime_quote, 'price', None)
        if price is None or not (isinstance(price, (int, float)) and price > 0):
            return df

        # Optional: skip augmentation on non-trading days (fail-open)
        enable_realtime_tech = getattr(
            self.config, 'enable_realtime_technical_indicators', True
        )
        if not enable_realtime_tech:
            return df
        market = get_market_for_stock(code)
        if market and not is_market_open(market, date.today()):
            return df

        last_val = df['date'].max()
        last_date = (
            last_val.date() if hasattr(last_val, 'date') else
            (last_val if isinstance(last_val, date) else pd.Timestamp(last_val).date())
        )
        yesterday_close = float(df.iloc[-1]['close']) if len(df) > 0 else price
        open_p = getattr(realtime_quote, 'open_price', None) or getattr(
            realtime_quote, 'pre_close', None
        ) or yesterday_close
        high_p = getattr(realtime_quote, 'high', None) or price
        low_p = getattr(realtime_quote, 'low', None) or price
        vol = getattr(realtime_quote, 'volume', None) or 0
        amt = getattr(realtime_quote, 'amount', None)
        pct = getattr(realtime_quote, 'change_pct', None)

        if last_date >= date.today():
            # Update last row with realtime close (copy to avoid mutating caller's df)
            df = df.copy()
            idx = df.index[-1]
            df.loc[idx, 'close'] = price
            if open_p is not None:
                df.loc[idx, 'open'] = open_p
            if high_p is not None:
                df.loc[idx, 'high'] = high_p
            if low_p is not None:
                df.loc[idx, 'low'] = low_p
            if vol:
                df.loc[idx, 'volume'] = vol
            if amt is not None:
                df.loc[idx, 'amount'] = amt
            if pct is not None:
                df.loc[idx, 'pct_chg'] = pct
        else:
            # Append virtual today row
            new_row = {
                'code': code,
                'date': date.today(),
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': price,
                'volume': vol,
                'amount': amt if amt is not None else 0,
                'pct_chg': pct if pct is not None else 0,
            }
            new_df = pd.DataFrame([new_row])
            df = pd.concat([df, new_df], ignore_index=True)
        return df

    def _build_context_snapshot(
        self,
        enhanced_context: Dict[str, Any],
        news_content: Optional[str],
        realtime_quote: Any,
        chip_data: Optional[ChipDistribution]
    ) -> Dict[str, Any]:
        """
        분석 컨텍스트 스냅샷 빌드
        """
        return {
            "enhanced_context": enhanced_context,
            "news_content": news_content,
            "realtime_quote_raw": self._safe_to_dict(realtime_quote),
            "chip_distribution_raw": self._safe_to_dict(chip_data),
        }

    @staticmethod
    def _safe_to_dict(value: Any) -> Optional[Dict[str, Any]]:
        """
        딕셔너리로 안전 변환
        """
        if value is None:
            return None
        if hasattr(value, "to_dict"):
            try:
                return value.to_dict()
            except Exception:
                return None
        if hasattr(value, "__dict__"):
            try:
                return dict(value.__dict__)
            except Exception:
                return None
        return None

    def _resolve_query_source(self, query_source: Optional[str]) -> str:
        """
        요청 출처 해석.

        우선순위（높은 것부터 낮은 것 순）：
        1. 명시적으로 전달된 query_source：호출 측에서 명확히 지정한 경우 우선 사용, 추론 결과 덮어쓰기 또는 미래 source_message가 bot이 아닌 경우 호환 가능
        2. source_message가 있으면 "bot"으로 추론：현재 약속은 봇 세션 컨텍스트
        3. query_id가 있으면 "web"으로 추론：Web 트리거 요청에는 query_id가 포함됨
        4. 기본 "system"：예약 작업 또는 CLI 등 위 컨텍스트 없을 때

        Args:
            query_source: 호출 측 명시 출처, 예："bot" / "web" / "cli" / "system"

        Returns:
            정규화된 출처 식별 문자열, 예："bot" / "web" / "cli" / "system"
        """
        if query_source:
            return query_source
        if self.source_message:
            return "bot"
        if self.query_id:
            return "web"
        return "system"

    def _build_query_context(self, query_id: Optional[str] = None) -> Dict[str, str]:
        """
        사용자 쿼리 연결 정보 생성
        """
        effective_query_id = query_id or self.query_id or ""

        context: Dict[str, str] = {
            "query_id": effective_query_id,
            "query_source": self.query_source or "",
        }

        if self.source_message:
            context.update({
                "requester_platform": self.source_message.platform or "",
                "requester_user_id": self.source_message.user_id or "",
                "requester_user_name": self.source_message.user_name or "",
                "requester_chat_id": self.source_message.chat_id or "",
                "requester_message_id": self.source_message.message_id or "",
                "requester_query": self.source_message.content or "",
            })

        return context
    
    def process_single_stock(
        self,
        code: str,
        skip_analysis: bool = False,
        single_stock_notify: bool = False,
        report_type: ReportType = ReportType.SIMPLE,
        analysis_query_id: Optional[str] = None,
    ) -> Optional[AnalysisResult]:
        """
        단일 종목의 전체 처리 흐름

        포함：
        1. 데이터 조회
        2. 데이터 저장
        3. AI 분석
        4. 단일 종목 알림（선택, #55）

        이 메서드는 스레드 풀에서 호출되며, 예외 처리 필요

        Args:
            analysis_query_id: 쿼리 연결 id
            code: 종목 코드
            skip_analysis: AI 분석 건너뜀 여부
            single_stock_notify: 단일 종목 알림 모드 활성화 여부（분석 완료 후 즉시 알림）
            report_type: 보고서 유형 열거형（설정에서 읽음, Issue #119）

        Returns:
            AnalysisResult 또는 None
        """
        logger.info(f"========== {code} 처리 시작 ==========")
        
        try:
            # Step 1: 데이터 조회 및 저장
            success, error = self.fetch_and_save_stock_data(code)
            
            if not success:
                logger.warning(f"[{code}] 데이터 조회 실패: {error}")
                # 조회 실패해도 보유 데이터로 분석 시도
            
            # Step 2: AI 분석
            if skip_analysis:
                logger.info(f"[{code}] AI 분석 건너뜀（dry-run 모드）")
                return None
            
            effective_query_id = analysis_query_id or self.query_id or uuid.uuid4().hex
            result = self.analyze_stock(code, report_type, query_id=effective_query_id)
            
            if result:
                logger.info(
                    f"[{code}] 분석 완료: {result.operation_advice}, "
                    f"점수 {result.sentiment_score}"
                )
                
                # 단일 종목 알림 모드（#55）：분석 완료 후 즉시 알림
                if single_stock_notify and self.notifier.is_available():
                    try:
                        # 보고서 유형에 따라 생성 방식 선택
                        if report_type == ReportType.FULL:
                            # 전체 보고서：의사결정 대시보드 형식 사용
                            report_content = self.notifier.generate_dashboard_report([result])
                            logger.info(f"[{code}] 전체 보고서 형식 사용")
                        else:
                            # 간략 보고서：단일 종목 보고서 형식（기본값）
                            report_content = self.notifier.generate_single_stock_report(result)
                            logger.info(f"[{code}] 간략 보고서 형식 사용")
                        
                        if self.notifier.send(report_content, email_stock_codes=[code]):
                            logger.info(f"[{code}] 단일 종목 알림 성공")
                        else:
                            logger.warning(f"[{code}] 단일 종목 알림 실패")
                    except Exception as e:
                        logger.error(f"[{code}] 단일 종목 알림 예외: {e}")
            
            return result
            
        except Exception as e:
            # 모든 예외 캡처, 단일 종목 실패가 전체에 영향 없도록
            logger.exception(f"[{code}] 처리 중 알 수 없는 예외 발생: {e}")
            return None
    
    def run(
        self,
        stock_codes: Optional[List[str]] = None,
        dry_run: bool = False,
        send_notification: bool = True,
        merge_notification: bool = False
    ) -> List[AnalysisResult]:
        """
        전체 분석 흐름 실행

        흐름：
        1. 분석 대상 종목 목록 조회
        2. 스레드 풀로 병렬 처리
        3. 분석 결과 수집
        4. 알림 발송

        Args:
            stock_codes: 종목 코드 목록（선택, 기본값은 설정의 관심 종목）
            dry_run: 데이터 조회만 하고 분석하지 않을 여부
            send_notification: 푸시 알림 발송 여부
            merge_notification: 알림 합산 여부（이번 알림 건너뛰고 main 레이어에서 개별 종목+시장 복기 후 일괄 발송, Issue #190）

        Returns:
            분석 결과 목록
        """
        start_time = time.time()
        
        # 설정의 종목 목록 사용
        if stock_codes is None:
            self.config.refresh_stock_list()
            stock_codes = self.config.stock_list
        
        if not stock_codes:
            logger.error("관심 종목 목록이 설정되지 않았습니다, .env 파일에서 STOCK_LIST를 설정하세요")
            return []
        
        logger.info(f"===== {len(stock_codes)}개 종목 분석 시작 =====")
        logger.info(f"종목 목록: {', '.join(stock_codes)}")
        logger.info(f"동시 처리 수: {self.max_workers}, 모드: {'데이터 조회만' if dry_run else '전체 분석'}")
        
        # === 실시간 시세 일괄 프리패치（최적화：각 종목마다 전체 데이터 로드 방지）===
        # 종목 수 >= 5일 때만 프리패치, 소수 종목은 개별 조회가 더 효율적
        if len(stock_codes) >= 5:
            prefetch_count = self.fetcher_manager.prefetch_realtime_quotes(stock_codes)
            if prefetch_count > 0:
                logger.info(f"일괄 프리패치 아키텍처 활성화：시장 데이터 한 번 로드, {len(stock_codes)}개 종목 캐시 공유")

        # Issue #455: 종목명 프리패치, 병렬 분석 시 「종목xxxxx」 표시 방지
        # dry_run은 데이터 조회만 하므로 종목명 프리패치 불필요, 추가 네트워크 오버헤드 방지
        if not dry_run:
            self.fetcher_manager.prefetch_stock_names(stock_codes, use_bulk=False)

        # 단일 종목 알림 모드（#55）：설정에서 읽기
        single_stock_notify = getattr(self.config, 'single_stock_notify', False)
        # Issue #119: 설정에서 보고서 유형 읽기
        report_type_str = getattr(self.config, 'report_type', 'simple').lower()
        report_type = ReportType.FULL if report_type_str == 'full' else ReportType.SIMPLE
        # Issue #128: 설정에서 분석 간격 읽기
        analysis_delay = getattr(self.config, 'analysis_delay', 0)

        if single_stock_notify:
            logger.info(f"단일 종목 알림 모드 활성화：분석 완료 후 즉시 알림（보고서 유형: {report_type_str}）")
        
        results: List[AnalysisResult] = []
        
        # 스레드 풀로 병렬 처리
        # 주의：max_workers를 낮게 설정（기본값 3）하여 봇 방지 트리거 방지
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_code = {
                executor.submit(
                    self.process_single_stock,
                    code,
                    skip_analysis=dry_run,
                    single_stock_notify=single_stock_notify and send_notification,
                    report_type=report_type,  # Issue #119: 보고서 유형 전달
                    analysis_query_id=uuid.uuid4().hex,
                ): code
                for code in stock_codes
            }
            
            # 결과 수집
            for idx, future in enumerate(as_completed(future_to_code)):
                code = future_to_code[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)

                    # Issue #128: 분석 간격 - 개별 종목 분석과 시장 분석 사이에 딜레이 추가
                    if idx < len(stock_codes) - 1 and analysis_delay > 0:
                        # 주의: 이 sleep은 “메인 스레드가 future를 수집하는 루프” 안에서 발생하며,
                        # 스레드 풀 내 작업들이 동시에 네트워크 요청을 시작하는 것을 막지 않습니다.
                        # 따라서 동시 요청 피크값을 낮추는 효과는 제한적이며, 실제 피크는 주로 max_workers가 결정합니다.
                        # 이 동작은 현재 유지됩니다（요구사항에 따라 로직 변경 없음）.
                        logger.debug(f"{analysis_delay}초 대기 후 다음 종목 진행...")
                        time.sleep(analysis_delay)

                except Exception as e:
                    logger.error(f"[{code}] 작업 실행 실패: {e}")
        
        # 통계
        elapsed_time = time.time() - start_time
        
        # dry-run 모드에서는 데이터 조회 성공을 성공으로 간주
        if dry_run:
            # 오늘 데이터가 있는 종목 확인
            success_count = sum(1 for code in stock_codes if self.db.has_today_data(code))
            fail_count = len(stock_codes) - success_count
        else:
            success_count = len(results)
            fail_count = len(stock_codes) - success_count
        
        logger.info("===== 분석 완료 =====")
        logger.info(f"성공: {success_count}, 실패: {fail_count}, 소요 시간: {elapsed_time:.2f}초")
        
        # 알림 발송（단일 종목 알림 모드에서는 요약 알림 건너뜀, 중복 방지）
        if results and send_notification and not dry_run:
            if single_stock_notify:
                # 단일 종목 알림 모드：요약 보고서만 저장, 반복 알림 없음
                logger.info("단일 종목 알림 모드：요약 알림 건너뜀, 로컬에 보고서만 저장")
                self._send_notifications(results, skip_push=True)
            elif merge_notification:
                # 합산 모드（Issue #190）：저장만 하고 알림 없음, main 레이어에서 개별 종목+시장 복기 후 일괄 발송
                logger.info("알림 합산 모드：이번 알림 건너뜀, 개별 종목+시장 복기 후 일괄 발송")
                self._send_notifications(results, skip_push=True)
            else:
                self._send_notifications(results)
        
        return results
    
    def _send_notifications(self, results: List[AnalysisResult], skip_push: bool = False) -> None:
        """
        분석 결과 알림 발송
        
        의사결정 대시보드 형식의 보고서 생성
        
        Args:
            results: 분석 결과 목록
            skip_push: 알림 건너뜀 여부（로컬에만 저장, 단일 종목 알림 모드 용도）
        """
        try:
            logger.info("의사결정 대시보드 일보 생성...")
            
            # 의사결정 대시보드 형식의 상세 일보 생성
            report = self.notifier.generate_dashboard_report(results)
            
            # 로컬에 저장
            filepath = self.notifier.save_report_to_file(report)
            logger.info(f"의사결정 대시보드 일보 저장 완료: {filepath}")
            
            # 알림 건너뜀（단일 종목 알림 모드）
            if skip_push:
                return
            
            # 알림 발송
            if self.notifier.is_available():
                channels = self.notifier.get_available_channels()
                context_success = self.notifier.send_to_context(report)

                # Issue #455: Markdown을 이미지로 변환（notification.send 로직과 동일）
                from src.md2img import markdown_to_image

                channels_needing_image = {
                    ch for ch in channels
                    if ch.value in self.notifier._markdown_to_image_channels
                }
                non_wechat_channels_needing_image = {
                    ch for ch in channels_needing_image if ch != NotificationChannel.WECHAT
                }

                def _get_md2img_hint() -> str:
                    try:
                        engine = getattr(get_config(), "md2img_engine", "wkhtmltoimage")
                    except Exception:
                        engine = "wkhtmltoimage"
                    return (
                        "npm i -g markdown-to-file" if engine == "markdown-to-file"
                        else "wkhtmltopdf (apt install wkhtmltopdf / brew install wkhtmltopdf)"
                    )

                image_bytes = None
                if non_wechat_channels_needing_image:
                    image_bytes = markdown_to_image(
                        report, max_chars=self.notifier._markdown_to_image_max_chars
                    )
                    if image_bytes:
                        logger.info(
                            "Markdown을 이미지로 변환 완료, %s에 이미지 발송",
                            [ch.value for ch in non_wechat_channels_needing_image],
                        )
                    else:
                        logger.warning(
                            "Markdown 이미지 변환 실패, 텍스트 발송으로 폴백. MARKDOWN_TO_IMAGE_CHANNELS 설정 확인 및 %s 설치 필요",
                            _get_md2img_hint(),
                        )

                # WeChat：간략 버전만 발송（플랫폼 제한）
                wechat_success = False
                if NotificationChannel.WECHAT in channels:
                    dashboard_content = self.notifier.generate_wechat_dashboard(results)
                    logger.info(f"WeChat 대시보드 길이: {len(dashboard_content)}자")
                    logger.debug(f"WeChat 푸시 내용:\n{dashboard_content}")
                    wechat_image_bytes = None
                    if NotificationChannel.WECHAT in channels_needing_image:
                        wechat_image_bytes = markdown_to_image(
                            dashboard_content,
                            max_chars=self.notifier._markdown_to_image_max_chars,
                        )
                        if wechat_image_bytes is None:
                            logger.warning(
                                "WeChat Markdown 이미지 변환 실패, 텍스트 발송으로 폴백. MARKDOWN_TO_IMAGE_CHANNELS 설정 확인 및 %s 설치 필요",
                                _get_md2img_hint(),
                            )
                    use_image = self.notifier._should_use_image_for_channel(
                        NotificationChannel.WECHAT, wechat_image_bytes
                    )
                    if use_image:
                        wechat_success = self.notifier._send_wechat_image(wechat_image_bytes)
                    else:
                        wechat_success = self.notifier.send_to_wechat(dashboard_content)

                # 기타 채널：전체 보고서 발송（커스텀 Webhook이 WeChat 잘라내기 로직에 오염되지 않도록）
                non_wechat_success = False
                stock_email_groups = getattr(self.config, 'stock_email_groups', []) or []
                for channel in channels:
                    if channel == NotificationChannel.WECHAT:
                        continue
                    if channel == NotificationChannel.FEISHU:
                        non_wechat_success = self.notifier.send_to_feishu(report) or non_wechat_success
                    elif channel == NotificationChannel.TELEGRAM:
                        use_image = self.notifier._should_use_image_for_channel(
                            channel, image_bytes
                        )
                        if use_image:
                            result = self.notifier._send_telegram_photo(image_bytes)
                        else:
                            result = self.notifier.send_to_telegram(report)
                        non_wechat_success = result or non_wechat_success
                    elif channel == NotificationChannel.EMAIL:
                        if stock_email_groups:
                            code_to_emails: Dict[str, Optional[List[str]]] = {}
                            for r in results:
                                if r.code not in code_to_emails:
                                    emails = []
                                    for stocks, emails_list in stock_email_groups:
                                        if r.code in stocks:
                                            emails.extend(emails_list)
                                    code_to_emails[r.code] = list(dict.fromkeys(emails)) if emails else None
                            emails_to_results: Dict[Optional[Tuple], List] = defaultdict(list)
                            for r in results:
                                recs = code_to_emails.get(r.code)
                                key = tuple(recs) if recs else None
                                emails_to_results[key].append(r)
                            for key, group_results in emails_to_results.items():
                                grp_report = self.notifier.generate_dashboard_report(group_results)
                                grp_image_bytes = None
                                if channel.value in self.notifier._markdown_to_image_channels:
                                    grp_image_bytes = markdown_to_image(
                                        grp_report,
                                        max_chars=self.notifier._markdown_to_image_max_chars,
                                    )
                                use_image = self.notifier._should_use_image_for_channel(
                                    channel, grp_image_bytes
                                )
                                receivers = list(key) if key is not None else None
                                if use_image:
                                    result = self.notifier._send_email_with_inline_image(
                                        grp_image_bytes, receivers=receivers
                                    )
                                else:
                                    result = self.notifier.send_to_email(
                                        grp_report, receivers=receivers
                                    )
                                non_wechat_success = result or non_wechat_success
                        else:
                            use_image = self.notifier._should_use_image_for_channel(
                                channel, image_bytes
                            )
                            if use_image:
                                result = self.notifier._send_email_with_inline_image(image_bytes)
                            else:
                                result = self.notifier.send_to_email(report)
                            non_wechat_success = result or non_wechat_success
                    elif channel == NotificationChannel.CUSTOM:
                        use_image = self.notifier._should_use_image_for_channel(
                            channel, image_bytes
                        )
                        if use_image:
                            result = self.notifier._send_custom_webhook_image(
                                image_bytes, fallback_content=report
                            )
                        else:
                            result = self.notifier.send_to_custom(report)
                        non_wechat_success = result or non_wechat_success
                    elif channel == NotificationChannel.PUSHPLUS:
                        non_wechat_success = self.notifier.send_to_pushplus(report) or non_wechat_success
                    elif channel == NotificationChannel.SERVERCHAN3:
                        non_wechat_success = self.notifier.send_to_serverchan3(report) or non_wechat_success
                    elif channel == NotificationChannel.DISCORD:
                        non_wechat_success = self.notifier.send_to_discord(report) or non_wechat_success
                    elif channel == NotificationChannel.PUSHOVER:
                        non_wechat_success = self.notifier.send_to_pushover(report) or non_wechat_success
                    elif channel == NotificationChannel.ASTRBOT:
                        non_wechat_success = self.notifier.send_to_astrbot(report) or non_wechat_success
                    else:
                        logger.warning(f"알 수 없는 알림 채널: {channel}")

                success = wechat_success or non_wechat_success or context_success
                if success:
                    logger.info("의사결정 대시보드 알림 성공")
                else:
                    logger.warning("의사결정 대시보드 알림 실패")
            else:
                logger.info("알림 채널 미설정, 알림 건너뜀")
                
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")

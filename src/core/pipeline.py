# -*- coding: utf-8 -*-
"""
===================================
KR/US stock intelligence analysis system - core analysis pipeline
===================================

Responsibilities:
1. Manage the full analysis process.
2. Coordinate data collection, storage, search, analysis, and notification modules.
3. Implement concurrency control and exception handling.
4. Provide core stock analysis capabilities.
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
    Main stock analysis process scheduler.
    
    Responsibilities:
    1. Manage the full analysis process.
    2. Coordinate data collection, storage, search, analysis, and notification modules.
    3. Implement concurrency control and exception handling.
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
        Initialize the scheduler.
        
        Args:
            config: Optional config object; defaults to the global config.
            max_workers: Optional maximum worker thread count; defaults to the configured value.
        """
        self.config = config or get_config()
        self.max_workers = max_workers or self.config.max_workers
        self.source_message = source_message
        self.query_id = query_id
        self.query_source = self._resolve_query_source(query_source)
        self.save_context_snapshot = (
            self.config.save_context_snapshot if save_context_snapshot is None else save_context_snapshot
        )
        
        # Initialize modules.
        self.db = get_db()
        self.fetcher_manager = DataFetcherManager()
        # Use the shared fetcher manager for enhanced data lookup.
        self.trend_analyzer = StockTrendAnalyzer()  # Trend analyzer.
        self.analyzer = GeminiAnalyzer()
        self.notifier = NotificationService(source_message=source_message)
        
        # Initialize the search service.
        self.search_service = SearchService(
            naver_keys=self.config.naver_api_keys,
            tavily_keys=self.config.tavily_api_keys,
            brave_keys=self.config.brave_api_keys,
            serpapi_keys=self.config.serpapi_keys,
            news_max_age_days=self.config.news_max_age_days,
        )
        
        logger.info(f"스케줄러 초기화 완료, 최대 동시 처리 수: {self.max_workers}")
        logger.info("추세 분석기 활성화 (MA5>MA10>MA20 강세 판단)")
        # Log realtime quote and chip distribution settings.
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
        Fetch and save data for a single stock.
        
        Checkpoint restart logic:
        1. Check whether today's data already exists in the database.
        2. Skip network requests when data exists and force refresh is disabled.
        3. Otherwise, fetch from the data source and save it.
        
        Args:
            code: Stock code.
            force_refresh: Whether to bypass the local cache and force refresh.
            
        Returns:
            Tuple of success flag and optional error message.
        """
        try:
            # Resolve the stock name first.
            stock_name = self.fetcher_manager.get_stock_name(code)

            today = date.today()
            # Note: checkpoint restart is based on calendar date.today().
            # On weekends, holidays, non-trading days, or when the server timezone differs from the market timezone:
            # - the latest trading-day data can still trigger another fetch because has_today_data returns False.
            # - date rollover or timezone offsets can incorrectly report that today's data exists.
            # Keep this behavior unchanged; a stricter implementation should compare against the latest trading day
            # or the latest date available from the data source.
            
            # Check checkpoint restart: skip when today's data already exists.
            if not force_refresh and self.db.has_today_data(code, today):
                logger.info(f"{stock_name}({code}) 오늘 데이터가 이미 있음, 조회 건너뜀（체크포인트 재시작）")
                return True, None

            # Fetch data from the data source.
            logger.info(f"{stock_name}({code}) 데이터 소스에서 데이터 조회 시작...")
            df, source_name = self.fetcher_manager.get_daily_data(code, days=30)

            if df is None or df.empty:
                return False, "조회된 데이터 없음"

            # Save to the database.
            saved_count = self.db.save_daily_data(df, code, source_name)
            logger.info(f"{stock_name}({code}) 데이터 저장 완료（출처: {source_name}, 신규 {saved_count}건）")

            return True, None

        except Exception as e:
            error_msg = f"데이터 조회/저장 실패: {str(e)}"
            logger.error(f"{stock_name}({code}) {error_msg}")
            return False, error_msg
    
    def analyze_stock(self, code: str, report_type: ReportType, query_id: str) -> Optional[AnalysisResult]:
        """
        Analyze a single stock with realtime, chip, trend, and search context.
        
        Flow:
        1. Fetch realtime quote data such as volume ratio and turnover, with DataFetcherManager failover.
        2. Fetch chip distribution data protected by the DataFetcherManager circuit breaker.
        3. Run trend analysis based on trading rules.
        4. Search multidimensional intelligence for news, risks, and earnings outlook.
        5. Load analysis context from the database.
        6. Call the AI analyzer.
        
        Args:
            query_id: Query correlation id.
            code: Stock code.
            report_type: Report type.
            
        Returns:
            AnalysisResult, or None when analysis fails.
        """
        try:
            # Resolve stock name; realtime quote can override it with the actual name.
            stock_name = self.fetcher_manager.get_stock_name(code)

            # Step 1: Fetch realtime quote data through the unified entry point with failover.
            realtime_quote = None
            try:
                realtime_quote = self.fetcher_manager.get_realtime_quote(code)
                if realtime_quote:
                    # Use the actual stock name returned by realtime quote data.
                    if realtime_quote.name:
                        stock_name = realtime_quote.name
                    # Keep compatibility across data sources; some sources may not expose volume_ratio.
                    volume_ratio = getattr(realtime_quote, 'volume_ratio', None)
                    turnover_rate = getattr(realtime_quote, 'turnover_rate', None)
                    logger.info(f"{stock_name}({code}) 실시간 시세: 가격={realtime_quote.price}, "
                              f"거래량비율={volume_ratio}, 회전율={turnover_rate}% "
                              f"(출처: {realtime_quote.source.value if hasattr(realtime_quote, 'source') else 'unknown'})")
                else:
                    logger.info(f"{stock_name}({code}) 실시간 시세 조회 실패 또는 비활성화, 과거 데이터로 분석 진행")
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 실시간 시세 조회 실패: {e}")

            # Fall back to a code-based placeholder when the name is still missing.
            if not stock_name:
                stock_name = f'종목{code}'

            # Step 2: Fetch chip distribution data through the unified entry point and circuit breaker.
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
            
            # Step 3: Run trend analysis based on trading rules.
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

            # Step 4: Search multidimensional intelligence for latest news, risks, and earnings outlook.
            news_context = None
            if self.search_service.is_available:
                logger.info(f"{stock_name}({code}) 다차원 정보 검색 시작...")

                # Use multidimensional search with at most five searches.
                intel_results = self.search_service.search_comprehensive_intel(
                    stock_code=code,
                    stock_name=stock_name,
                    max_searches=5
                )

                # Format the intelligence report.
                if intel_results:
                    news_context = self.search_service.format_intel_report(intel_results, stock_name)
                    total_results = sum(
                        len(r.results) for r in intel_results.values() if r.success
                    )
                    logger.info(f"{stock_name}({code}) 정보 검색 완료: 총 {total_results}건 결과")
                    logger.debug(f"{stock_name}({code}) 정보 검색 결과:\n{news_context}")

                    # Save news intelligence for later review and lookup.
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

            # Step 5: Load analysis context with technical data.
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
            
            # Step 6: Enhance context with realtime quote, chip, trend, and stock name data.
            enhanced_context = self._enhance_context(
                context, 
                realtime_quote, 
                chip_data, 
                trend_result,
                stock_name  # Pass the stock name.
            )
            
            # Step 7: Call AI analysis with enhanced context and news.
            result = self.analyzer.analyze(enhanced_context, news_context=news_context)

            # Step 7.5: Populate price fields on the result.
            if result:
                realtime_data = enhanced_context.get('realtime', {})
                result.current_price = realtime_data.get('price')
                result.change_pct = realtime_data.get('change_pct')

            # Step 8: Save analysis history.
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
        Enhance analysis context.
        
        Adds realtime quote, chip distribution, trend analysis, and stock name data to the context.
        
        Args:
            context: Original context.
            realtime_quote: Realtime quote data, or None.
            chip_data: Chip distribution data.
            trend_result: Trend analysis result.
            stock_name: Stock name.
            
        Returns:
            Enhanced context.
        """
        enhanced = context.copy()
        
        # Add stock name.
        if stock_name:
            enhanced['stock_name'] = stock_name
        elif realtime_quote and getattr(realtime_quote, 'name', None):
            enhanced['stock_name'] = realtime_quote.name
        
        # Add realtime quote data while tolerating data-source field differences.
        if realtime_quote:
            # Use getattr so missing fields resolve to None or defaults.
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
            # Drop None values to keep context size smaller.
            enhanced['realtime'] = {k: v for k, v in enhanced['realtime'].items() if v is not None}
        
        # Add chip distribution data.
        if chip_data:
            current_price = getattr(realtime_quote, 'price', 0) if realtime_quote else 0
            enhanced['chip'] = {
                'profit_ratio': chip_data.profit_ratio,
                'avg_cost': chip_data.avg_cost,
                'concentration_90': chip_data.concentration_90,
                'concentration_70': chip_data.concentration_70,
                'chip_status': chip_data.get_chip_status(current_price or 0),
            }
        
        # Add trend analysis results.
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
        Analyze a single stock in Agent mode.
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

            # Run Agent analysis.
            message = f"종목 {code} ({stock_name})를 분석하고 의사결정 대시보드 보고서를 생성해 주세요."
            agent_result = executor.run(message, context=initial_context)

            # Convert to AnalysisResult.
            result = self._agent_result_to_analysis_result(agent_result, code, stock_name, report_type, query_id)
            resolved_stock_name = result.name if result and result.name else stock_name

            # Save news intelligence separately because Agent tool results are only used for LLM context
            # and are not persisted (Fixes #396).
            # Use search_stock_news to match Agent tool behavior with one API call and no extra delay.
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

            # Save analysis history.
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
        Convert AgentResult to AnalysisResult.
        """
        result = AnalysisResult(
            code=code,
            name=stock_name,
            sentiment_score=50,
            trend_prediction="알 수 없음",
            operation_advice="관망",
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
            result.trend_prediction = dash.get("trend_prediction", "알 수 없음")
            result.operation_advice = dash.get("operation_advice", "관망")
            result.decision_type = dash.get("decision_type", "hold")
            result.analysis_summary = dash.get("analysis_summary", "")
            # The AI returns a top-level dict that contains a nested 'dashboard' sub-key
            # with core_conclusion / battle_plan / intelligence.  AnalysisResult's helper
            # methods (get_sniper_points, get_core_conclusion, etc.) expect that inner
            # structure, so we unwrap it here.
            result.dashboard = dash.get("dashboard") or dash
        else:
            result.sentiment_score = 50
            result.operation_advice = "관망"
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
        if normalized.startswith("종목"):
            return True
        if "Unknown" in normalized:
            return True
        return False

    @staticmethod
    def _safe_int(value: Any, default: int = 50) -> int:
        """Safely convert a value to an integer."""
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
        Describe volume ratio.
        
        Volume ratio = current volume / prior 5-day average volume.
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
        Build an analysis context snapshot.
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
        Safely convert a value to a dictionary.
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
        Resolve the request source.

        Priority, highest to lowest:
        1. Explicit query_source from the caller, which overrides inferred results and supports future
           non-bot source_message contexts.
        2. source_message implies "bot" under the current bot session contract.
        3. query_id implies "web" because web-triggered requests include query_id.
        4. Default to "system" for scheduled jobs, CLI runs, and other contexts.

        Args:
            query_source: Explicit caller source, such as "bot", "web", "cli", or "system".

        Returns:
            Normalized source identifier, such as "bot", "web", "cli", or "system".
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
        Build user query correlation context.
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
        Run the full processing flow for one stock.

        Includes:
        1. Data fetch.
        2. Data save.
        3. AI analysis.
        4. Optional single-stock notification (#55).

        This method is called from a thread pool and must handle exceptions.

        Args:
            analysis_query_id: Query correlation id.
            code: Stock code.
            skip_analysis: Whether to skip AI analysis.
            single_stock_notify: Whether to notify immediately after this stock analysis completes.
            report_type: Report type enum read from config (Issue #119).

        Returns:
            AnalysisResult, or None.
        """
        logger.info(f"========== {code} 처리 시작 ==========")
        
        try:
            # Step 1: Fetch and save data.
            success, error = self.fetch_and_save_stock_data(code)
            
            if not success:
                logger.warning(f"[{code}] 데이터 조회 실패: {error}")
                # Continue analysis with existing data when fetching fails.
            
            # Step 2: AI analysis.
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
                
                # Single-stock notification mode (#55): notify immediately after analysis.
                if single_stock_notify and self.notifier.is_available():
                    try:
                        # Choose generation method by report type.
                        if report_type == ReportType.FULL:
                            # Full report: use the decision dashboard format.
                            report_content = self.notifier.generate_dashboard_report([result])
                            logger.info(f"[{code}] 전체 보고서 형식 사용")
                        else:
                            # Simple report: use the single-stock report format by default.
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
            # Capture all exceptions so a single-stock failure does not affect the full run.
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
        Run the full analysis flow.

        Flow:
        1. Load the target stock list.
        2. Process stocks in parallel with a thread pool.
        3. Collect analysis results.
        4. Send notifications.

        Args:
            stock_codes: Optional stock code list; defaults to configured watchlist.
            dry_run: Whether to fetch data only and skip analysis.
            send_notification: Whether to send push notifications.
            merge_notification: Whether to skip this notification so the main layer can send merged stock and
                market review notifications (Issue #190).

        Returns:
            Analysis results.
        """
        start_time = time.time()
        
        # Use the configured stock list.
        if stock_codes is None:
            self.config.refresh_stock_list()
            stock_codes = self.config.stock_list
        
        if not stock_codes:
            logger.error("관심 종목 목록이 설정되지 않았습니다, .env 파일에서 STOCK_LIST를 설정하세요")
            return []
        
        logger.info(f"===== {len(stock_codes)}개 종목 분석 시작 =====")
        logger.info(f"종목 목록: {', '.join(stock_codes)}")
        logger.info(f"동시 처리 수: {self.max_workers}, 모드: {'데이터 조회만' if dry_run else '전체 분석'}")
        
        # === Batch realtime quote prefetch ===
        # Prefetch only when there are at least five stocks; individual fetches are cheaper for smaller batches.
        if len(stock_codes) >= 5:
            prefetch_count = self.fetcher_manager.prefetch_realtime_quotes(stock_codes)
            if prefetch_count > 0:
                logger.info(f"일괄 프리패치 아키텍처 활성화：시장 데이터 한 번 로드, {len(stock_codes)}개 종목 캐시 공유")

        # Issue #455: Prefetch stock names to avoid code-based placeholders during parallel analysis.
        # dry_run only fetches data, so skip name prefetching to avoid extra network overhead.
        if not dry_run:
            self.fetcher_manager.prefetch_stock_names(stock_codes, use_bulk=False)

        # Read single-stock notification mode from config (#55).
        single_stock_notify = getattr(self.config, 'single_stock_notify', False)
        # Issue #119: Read report type from config.
        report_type_str = getattr(self.config, 'report_type', 'simple').lower()
        report_type = ReportType.FULL if report_type_str == 'full' else ReportType.SIMPLE
        # Issue #128: Read analysis delay from config.
        analysis_delay = getattr(self.config, 'analysis_delay', 0)

        if single_stock_notify:
            logger.info(f"단일 종목 알림 모드 활성화：분석 완료 후 즉시 알림（보고서 유형: {report_type_str}）")
        
        results: List[AnalysisResult] = []
        
        # Process in parallel with a thread pool.
        # Keep max_workers low by default to reduce anti-bot trigger risk.
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit jobs.
            future_to_code = {
                executor.submit(
                    self.process_single_stock,
                    code,
                    skip_analysis=dry_run,
                    single_stock_notify=single_stock_notify and send_notification,
                    report_type=report_type,  # Issue #119: Pass report type.
                    analysis_query_id=uuid.uuid4().hex,
                ): code
                for code in stock_codes
            }
            
            # Collect results.
            for idx, future in enumerate(as_completed(future_to_code)):
                code = future_to_code[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)

                    # Issue #128: Add delay between individual stock analyses.
                    if idx < len(stock_codes) - 1 and analysis_delay > 0:
                        # This sleep happens while the main thread collects futures, so it does not prevent
                        # thread-pool workers from starting network requests concurrently. It only has limited
                        # effect on peak concurrency; max_workers is the primary control. Keep behavior unchanged.
                        logger.debug(f"{analysis_delay}초 대기 후 다음 종목 진행...")
                        time.sleep(analysis_delay)

                except Exception as e:
                    logger.error(f"[{code}] 작업 실행 실패: {e}")
        
        # Statistics.
        elapsed_time = time.time() - start_time
        
        # In dry-run mode, successful data fetch counts as success.
        if dry_run:
            # Check which stocks have today's data.
            success_count = sum(1 for code in stock_codes if self.db.has_today_data(code))
            fail_count = len(stock_codes) - success_count
        else:
            success_count = len(results)
            fail_count = len(stock_codes) - success_count
        
        logger.info("===== 분석 완료 =====")
        logger.info(f"성공: {success_count}, 실패: {fail_count}, 소요 시간: {elapsed_time:.2f}초")
        
        # Send notifications; skip summary push in single-stock mode to avoid duplicates.
        if results and send_notification and not dry_run:
            if single_stock_notify:
                # Single-stock notification mode: save summary report only, with no repeated push.
                logger.info("단일 종목 알림 모드：요약 알림 건너뜀, 로컬에 보고서만 저장")
                self._send_notifications(results, skip_push=True)
            elif merge_notification:
                # Merge mode (Issue #190): save only; the main layer sends stock and market reviews together.
                logger.info("알림 합산 모드：이번 알림 건너뜀, 개별 종목+시장 복기 후 일괄 발송")
                self._send_notifications(results, skip_push=True)
            else:
                self._send_notifications(results)
        
        return results
    
    def _send_notifications(self, results: List[AnalysisResult], skip_push: bool = False) -> None:
        """
        Send analysis result notifications.
        
        Generates a report in decision dashboard format.
        
        Args:
            results: Analysis results.
            skip_push: Whether to skip push delivery and save only, used by single-stock notification mode.
        """
        try:
            logger.info("의사결정 대시보드 일보 생성...")
            
            # Generate a detailed daily report in decision dashboard format.
            report = self.notifier.generate_dashboard_report(results)
            
            # Save locally.
            filepath = self.notifier.save_report_to_file(report)
            logger.info(f"의사결정 대시보드 일보 저장 완료: {filepath}")
            
            # Skip notification delivery for single-stock notification mode.
            if skip_push:
                return
            
            # Send notifications.
            if self.notifier.is_available():
                channels = self.notifier.get_available_channels()
                context_success = self.notifier.send_to_context(report)

                # Issue #455: Convert Markdown to an image, matching notification.send behavior.
                from src.md2img import markdown_to_image

                channels_needing_image = {
                    ch for ch in channels
                    if ch.value in self.notifier._markdown_to_image_channels
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
                if channels_needing_image:
                    image_bytes = markdown_to_image(
                        report, max_chars=self.notifier._markdown_to_image_max_chars
                    )
                    if image_bytes:
                        logger.info(
                            "Markdown을 이미지로 변환 완료, %s에 이미지 발송",
                            [ch.value for ch in channels_needing_image],
                        )
                    else:
                        logger.warning(
                            "Markdown 이미지 변환 실패, 텍스트 발송으로 폴백. MARKDOWN_TO_IMAGE_CHANNELS 설정 확인 및 %s 설치 필요",
                            _get_md2img_hint(),
                        )

                # Send the full report to all retained notification channels.
                notification_success = False
                stock_email_groups = getattr(self.config, 'stock_email_groups', []) or []
                for channel in channels:
                    if channel == NotificationChannel.TELEGRAM:
                        use_image = self.notifier._should_use_image_for_channel(
                            channel, image_bytes
                        )
                        if use_image:
                            result = self.notifier._send_telegram_photo(image_bytes)
                        else:
                            result = self.notifier.send_to_telegram(report)
                        notification_success = result or notification_success
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
                                notification_success = result or notification_success
                        else:
                            use_image = self.notifier._should_use_image_for_channel(
                                channel, image_bytes
                            )
                            if use_image:
                                result = self.notifier._send_email_with_inline_image(image_bytes)
                            else:
                                result = self.notifier.send_to_email(report)
                            notification_success = result or notification_success
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
                        notification_success = result or notification_success
                    elif channel == NotificationChannel.DISCORD:
                        notification_success = self.notifier.send_to_discord(report) or notification_success
                    elif channel == NotificationChannel.PUSHOVER:
                        notification_success = self.notifier.send_to_pushover(report) or notification_success
                    elif channel == NotificationChannel.ASTRBOT:
                        notification_success = self.notifier.send_to_astrbot(report) or notification_success
                    else:
                        logger.warning(f"알 수 없는 알림 채널: {channel}")

                success = notification_success or context_success
                if success:
                    logger.info("의사결정 대시보드 알림 성공")
                else:
                    logger.warning("의사결정 대시보드 알림 실패")
            else:
                logger.info("알림 채널 미설정, 알림 건너뜀")
                
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")

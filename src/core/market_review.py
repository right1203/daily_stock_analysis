# -*- coding: utf-8 -*-
"""
===================================
주식 지능형 분석 시스템 - 시장 복기 모듈（A주 / 미국주 지원）
===================================

역할：
1. MARKET_REVIEW_REGION 설정에 따라 시장 지역 선택（kr / us / both）
2. 시장 복기 분석 실행 및 복기 보고서 생성
3. 복기 보고서 저장 및 전송
"""

import logging
from datetime import datetime
from typing import Optional

from src.config import get_config
from src.notification import NotificationService
from src.market_analyzer import MarketAnalyzer
from src.search_service import SearchService
from src.analyzer import GeminiAnalyzer


logger = logging.getLogger(__name__)


def run_market_review(
    notifier: NotificationService,
    analyzer: Optional[GeminiAnalyzer] = None,
    search_service: Optional[SearchService] = None,
    send_notification: bool = True,
    merge_notification: bool = False,
    override_region: Optional[str] = None,
) -> Optional[str]:
    """
    시장 복기 분석 실행

    Args:
        notifier: 알림 서비스
        analyzer: AI 분석기（선택사항）
        search_service: 검색 서비스（선택사항）
        send_notification: 알림 전송 여부
        merge_notification: 합산 푸시 여부（이번 푸시 건너뜀, main 레이어에서 개별종목+시장복기 통합 전송, Issue #190）
        override_region: config의 market_review_region 덮어쓰기（Issue #373 거래일 필터링 후 유효 서브셋）

    Returns:
        복기 보고서 텍스트
    """
    logger.info("시장 복기 분석 시작...")
    config = get_config()
    region = (
        override_region
        if override_region is not None
        else (getattr(config, 'market_review_region', 'kr') or 'kr')
    )
    if region not in ('kr', 'us', 'both'):
        region = 'kr'

    try:
        if region == 'both':
            # 순서대로 한국 + 미국 시장 복기 실행, 보고서 합산
            kr_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='kr'
            )
            us_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='us'
            )
            logger.info("한국 시장 복기 보고서 생성 중...")
            cn_report = kr_analyzer.run_daily_review()
            logger.info("미국 시장 복기 보고서 생성 중...")
            us_report = us_analyzer.run_daily_review()
            review_report = ''
            if cn_report:
                review_report = f"# 한국 시장 복기\n\n{cn_report}"
            if us_report:
                if review_report:
                    review_report += "\n\n---\n\n> 이하 미국 시장 복기\n\n"
                review_report += f"# 미국 시장 복기\n\n{us_report}"
            if not review_report:
                review_report = None
        else:
            market_analyzer = MarketAnalyzer(
                search_service=search_service,
                analyzer=analyzer,
                region=region,
            )
            review_report = market_analyzer.run_daily_review()
        
        if review_report:
            # 보고서를 파일로 저장
            date_str = datetime.now().strftime('%Y%m%d')
            report_filename = f"market_review_{date_str}.md"
            filepath = notifier.save_report_to_file(
                f"# 🎯 시장 복기\n\n{review_report}", 
                report_filename
            )
            logger.info(f"시장 복기 보고서 저장 완료: {filepath}")
            
            # 알림 전송（합산 모드에서는 건너뜀, main 레이어에서 통합 전송）
            if merge_notification and send_notification:
                logger.info("합산 푸시 모드: 시장 복기 단독 푸시 건너뜀, 개별종목+시장복기 후 통합 전송 예정")
            elif send_notification and notifier.is_available():
                # 제목 추가
                report_content = f"🎯 시장 복기\n\n{review_report}"

                success = notifier.send(report_content, email_send_to_all=True)
                if success:
                    logger.info("시장 복기 푸시 성공")
                else:
                    logger.warning("시장 복기 푸시 실패")
            elif not send_notification:
                logger.info("알림 전송 건너뜀 (--no-notify)")
            
            return review_report
        
    except Exception as e:
        logger.error(f"시장 복기 분석 실패: {e}")
    
    return None

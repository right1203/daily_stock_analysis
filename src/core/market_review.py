# -*- coding: utf-8 -*-
"""
===================================
Stock intelligence analysis system - market review module (KR / US support)
===================================

Responsibilities:
1. Select the market region from MARKET_REVIEW_REGION (kr / us / both).
2. Run market review analysis and generate the review report.
3. Save and send the review report.
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
    Run market review analysis.

    Args:
        notifier: Notification service.
        analyzer: Optional AI analyzer.
        search_service: Optional search service.
        send_notification: Whether to send notifications.
        merge_notification: Skip this push so the main layer can send the merged stock and market review
            notification (Issue #190).
        override_region: Override config.market_review_region after trading-day filtering selects a valid subset
            (Issue #373).

    Returns:
        Market review report text.
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
            # Run KR and US market reviews in order, then combine the reports.
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
            # Save the report to a file.
            date_str = datetime.now().strftime('%Y%m%d')
            report_filename = f"market_review_{date_str}.md"
            filepath = notifier.save_report_to_file(
                f"# 🎯 시장 복기\n\n{review_report}", 
                report_filename
            )
            logger.info(f"시장 복기 보고서 저장 완료: {filepath}")
            
            # Send the notification unless merge mode delegates it to the main layer.
            if merge_notification and send_notification:
                logger.info("합산 푸시 모드: 시장 복기 단독 푸시 건너뜀, 개별종목+시장복기 후 통합 전송 예정")
            elif send_notification and notifier.is_available():
                # Add the title.
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

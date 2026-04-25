# -*- coding: utf-8 -*-
"""
===================================
Market Review Command
===================================

Run market review analysis and produce a market overview report.
"""

import logging
import threading
from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse

logger = logging.getLogger(__name__)


class MarketCommand(BotCommand):
    """
    Market review command.

    Executes market review analysis including:
    - Major index performance
    - Sector highlights
    - Market sentiment
    - Near-term outlook

    Usage:
        /market - run market review
    """

    @property
    def name(self) -> str:
        return "market"

    @property
    def aliases(self) -> List[str]:
        return ["m", "시장", "복기", "시황"]

    @property
    def description(self) -> str:
        return "시장 복기 분석"

    @property
    def usage(self) -> str:
        return "/market"

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute market review command."""
        logger.info("[MarketCommand] Start market review analysis")

        # Run in a background thread (avoid blocking command handling)
        thread = threading.Thread(
            target=self._run_market_review,
            args=(message,),
            daemon=True
        )
        thread.start()

        return BotResponse.markdown_response(
            "✅ **大盘复盘任务已启动**\n\n"
            "다음 항목을 분석합니다:\n"
            "• 주요 지수 흐름\n"
            "• 업종/테마 동향\n"
            "• 시장 심리\n"
            "• 단기 전망\n\n"
            "완료되면 결과가 자동으로 전송됩니다."
        )

    def _run_market_review(self, message: BotMessage) -> None:
        """Execute market review in the background."""
        try:
            from src.config import get_config
            from src.notification import NotificationService
            from src.market_analyzer import MarketAnalyzer
            from src.search_service import SearchService
            from src.analyzer import GeminiAnalyzer

            config = get_config()
            notifier = NotificationService(source_message=message)

            # Initialize search service
            search_service = None
            if config.bocha_api_keys or config.tavily_api_keys or config.brave_api_keys or config.serpapi_keys:
                search_service = SearchService(
                    bocha_keys=config.bocha_api_keys,
                    tavily_keys=config.tavily_api_keys,
                    brave_keys=config.brave_api_keys,
                    serpapi_keys=config.serpapi_keys,
                    news_max_age_days=config.news_max_age_days,
                )

            # Initialize AI analyzer
            analyzer = None
            if config.gemini_api_key or config.openai_api_key:
                analyzer = GeminiAnalyzer()

            # Use market region from config for consistency with scheduler/CLI
            region = getattr(config, 'market_review_region', 'kr')

            # Run review
            market_analyzer = MarketAnalyzer(
                search_service=search_service,
                analyzer=analyzer,
                region=region,
            )

            review_report = market_analyzer.run_daily_review()

            if review_report:
                # Send result
                report_content = f"🎯 **시장 복기**\n\n{review_report}"
                notifier.send(report_content, email_send_to_all=True)
                logger.info("[MarketCommand] Market review completed and sent")
            else:
                logger.warning("[MarketCommand] Market review returned empty result")

        except Exception as e:
            logger.error(f"[MarketCommand] Market review failed: {e}")
            logger.exception(e)

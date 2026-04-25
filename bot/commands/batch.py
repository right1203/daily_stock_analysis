# -*- coding: utf-8 -*-
"""Batch analysis command for configured watchlist stocks."""

import logging
import threading
import uuid
from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse

logger = logging.getLogger(__name__)


class BatchCommand(BotCommand):
    """
    Batch analysis command.

    Analyzes the configured watchlist and generates a summary report.

    Usage:
        /batch      - Analyze all watchlist stocks.
        /batch 3    - Analyze only the first 3 stocks.
    """
    
    @property
    def name(self) -> str:
        return "batch"
    
    @property
    def aliases(self) -> List[str]:
        return ["b", "일괄", "전체"]
    
    @property
    def description(self) -> str:
        return "관심 종목 일괄 분석"
    
    @property
    def usage(self) -> str:
        return "/batch [count]"
    
    @property
    def admin_only(self) -> bool:
        """Whether batch analysis requires admin privileges."""
        return False
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the batch analysis command."""
        from src.config import get_config
        
        config = get_config()
        config.refresh_stock_list()
        
        stock_list = config.stock_list
        
        if not stock_list:
            return BotResponse.error_response(
                "관심 종목 목록이 비어 있습니다. 먼저 STOCK_LIST를 설정해 주세요"
            )
        
        # Parse count argument.
        limit = None
        if args:
            try:
                limit = int(args[0])
                if limit <= 0:
                    return BotResponse.error_response("수량은 0보다 커야 합니다")
            except ValueError:
                return BotResponse.error_response(f"유효하지 않은 수량: {args[0]}")
        
        # Apply count limit.
        if limit:
            stock_list = stock_list[:limit]
        
        logger.info("[BatchCommand] Starting batch analysis for %d stocks", len(stock_list))
        
        # Run analysis in a background thread.
        thread = threading.Thread(
            target=self._run_batch_analysis,
            args=(stock_list, message),
            daemon=True
        )
        thread.start()
        
        return BotResponse.markdown_response(
            f"✅ **일괄 분석 작업이 시작되었습니다**\n\n"
            f"• 분석 종목 수: {len(stock_list)}개\n"
            f"• 종목 목록: {', '.join(stock_list[:5])}"
            f"{'...' if len(stock_list) > 5 else ''}\n\n"
            f"분석이 완료되면 요약 리포트가 자동으로 전송됩니다."
        )
    
    def _run_batch_analysis(self, stock_list: List[str], message: BotMessage) -> None:
        """Run batch analysis in the background."""
        try:
            from src.config import get_config
            from main import StockAnalysisPipeline
            
            config = get_config()
            
            # Create analysis pipeline.
            pipeline = StockAnalysisPipeline(
                config=config,
                source_message=message,
                query_id=uuid.uuid4().hex,
                query_source="bot"
            )
            
            # Execute analysis; notification is sent by the pipeline.
            results = pipeline.run(
                stock_codes=stock_list,
                dry_run=False,
                send_notification=True
            )
            
            logger.info("[BatchCommand] Batch analysis completed, successful: %d", len(results))
            
        except Exception as e:
            logger.error("[BatchCommand] Batch analysis failed: %s", e)
            logger.exception(e)

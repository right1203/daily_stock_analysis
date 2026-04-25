# -*- coding: utf-8 -*-
"""
===================================
Stock Analysis Command
===================================

Analyze a requested stock and generate an AI report.
"""

import re
import logging
from typing import List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from data_provider.base import canonical_stock_code

logger = logging.getLogger(__name__)


class AnalyzeCommand(BotCommand):
    """
    Stock analysis command.

    Analyzes a stock code and sends an AI report.

    Usage:
        /analyze 005930       - Analyze Samsung Electronics (simple report)
        /analyze 005930 full  - Analyze and generate full report
    """
    
    @property
    def name(self) -> str:
        return "analyze"
    
    @property
    def aliases(self) -> List[str]:
        return ["a", "분석"]
    
    @property
    def description(self) -> str:
        return "Analyze a stock"
    
    @property
    def usage(self) -> str:
        return "/analyze <stock_code> [full]"
    
    def validate_args(self, args: List[str]) -> Optional[str]:
        """Validate command arguments."""
        if not args:
            return "종목 코드를 입력하세요."
        
        code = args[0].upper()

        # Validate code format
        # KR: 6-digit numeric code
        # US: 1-5 uppercase letters with optional class suffix (e.g. BRK.B)
        is_a_stock = re.match(r'^\d{6}$', code)
        is_us_stock = re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code)

        if not (is_a_stock or is_us_stock):
            return f"유효하지 않은 종목 코드: {code} (KR: 6 digits / US: 1-5 letters)"
        
        return None
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute analysis command."""
        code = canonical_stock_code(args[0])
        
        # Decide report type (default: simple; full/완전/상세 => full)
        report_type = "simple"
        if len(args) > 1 and args[1].lower() in ["full", "完整", "详细"]:
            report_type = "full"
        logger.info(f"[AnalyzeCommand] Analyze stock: {code}, report_type: {report_type}")
        
        try:
            # Call analysis service
            from src.services.task_service import get_task_service
            from src.enums import ReportType
            
            service = get_task_service()
            
            # Submit async analysis task
            result = service.submit_analysis(
                code=code,
                report_type=ReportType.from_str(report_type),
                source_message=message
            )
            
            if result.get("success"):
                task_id = result.get("task_id", "")
                return BotResponse.markdown_response(
                    f"✅ **分析任务已提交**\n\n"
                    f"• 종목 코드: `{code}`\n"
                    f"• 보고서 유형: {ReportType.from_str(report_type).display_name}\n"
                    f"• 작업 ID: `{task_id[:20]}...`\n\n"
                    f"분석이 완료되면 결과가 자동으로 전송됩니다."
                )
            else:
                error = result.get("error", "Unknown error")
                return BotResponse.error_response(f"작업 제출 실패: {error}")
                
        except Exception as e:
            logger.error(f"[AnalyzeCommand] Execution failed: {e}")
            return BotResponse.error_response(f"분석 실패: {str(e)[:100]}")

# -*- coding: utf-8 -*-
"""
===================================
Status Command
===================================

Display system runtime and configuration status.
"""

import platform
import sys
from datetime import datetime
from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse


class StatusCommand(BotCommand):
    """
    Status command.

    Displays runtime status including:
    - service status
    - key configuration
    - available capabilities
    """
    
    @property
    def name(self) -> str:
        return "status"
    
    @property
    def aliases(self) -> List[str]:
        return ["s", "상태", "info"]
    
    @property
    def description(self) -> str:
        return "시스템 상태 표시"
    
    @property
    def usage(self) -> str:
        return "/status"
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute status command."""
        from src.config import get_config
        
        config = get_config()
        
        # Collect status information
        status_info = self._collect_status(config)
        
        # Format output
        text = self._format_status(status_info, message.platform)
        
        return BotResponse.markdown_response(text)
    
    def _collect_status(self, config) -> dict:
        """Collect system status information."""
        status = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "stock_count": len(config.stock_list),
            "stock_list": config.stock_list[:5],  # show first 5 only
        }
        
        # AI configuration state
        status["ai_gemini"] = bool(config.gemini_api_key)
        status["ai_openai"] = bool(config.openai_api_key)
        
        # Search provider state
        status["search_naver"] = len(getattr(config, "naver_api_keys", []) or []) > 0
        status["search_tavily"] = len(getattr(config, "tavily_api_keys", []) or []) > 0
        status["search_brave"] = len(getattr(config, "brave_api_keys", []) or []) > 0
        status["search_serpapi"] = len(getattr(config, "serpapi_keys", []) or []) > 0
        
        # Notification channel state
        status["notify_discord"] = bool(getattr(config, "discord_webhook_url", None))
        status["notify_telegram"] = bool(config.telegram_bot_token and config.telegram_chat_id)
        status["notify_email"] = bool(config.email_sender and config.email_password)
        
        return status
    
    def _format_status(self, status: dict, platform: str) -> str:
        """Format status information."""
        # Status icon
        def icon(enabled: bool) -> str:
            return "✅" if enabled else "❌"
        
        lines = [
            "📊 **주식 분석 도우미 - 시스템 상태**",
            "",
            f"🕐 时间: {status['timestamp']}",
            f"🐍 Python: {status['python_version']}",
            f"💻 Platform: {status['platform']}",
            "",
            "---",
            "",
            "**📈 관심 종목 설정**",
            f"• 종목 수: {status['stock_count']}",
        ]
        
        if status['stock_list']:
            stocks_preview = ", ".join(status['stock_list'])
            if status['stock_count'] > 5:
                stocks_preview += f" ... 等 {status['stock_count']} 只"
            lines.append(f"• 종목 목록: {stocks_preview}")
        
        lines.extend([
            "",
            "**🤖 AI 분석 서비스**",
            f"• Gemini API: {icon(status['ai_gemini'])}",
            f"• OpenAI API: {icon(status['ai_openai'])}",
            "",
            "**🔍 검색 서비스**",
            f"• Naver: {icon(status['search_naver'])}",
            f"• Tavily: {icon(status['search_tavily'])}",
            f"• Brave: {icon(status['search_brave'])}",
            f"• SerpAPI: {icon(status['search_serpapi'])}",
            "",
            "**📢 알림 채널**",
            f"• Discord: {icon(status['notify_discord'])}",
            f"• Telegram: {icon(status['notify_telegram'])}",
            f"• Email: {icon(status['notify_email'])}",
        ])
        
        # Overall AI service status
        ai_available = status['ai_gemini'] or status['ai_openai']
        if ai_available:
            lines.extend([
                "",
                "---",
                "✅ **시스템 준비 완료: 분석을 시작할 수 있습니다.**",
            ])
        else:
            lines.extend([
                "",
                "---",
                "⚠️ **AI 서비스가 설정되지 않아 분석 기능을 사용할 수 없습니다.**",
                "Gemini 또는 OpenAI API Key를 설정해 주세요.",
            ])
        
        return "\n".join(lines)

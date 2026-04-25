# -*- coding: utf-8 -*-
"""
===================================
Help Command
===================================

Display available commands and usage details.
"""

from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse


class HelpCommand(BotCommand):
    """
    Help command.

    Shows all available commands and detailed usage.

    Usage:
        /help         - Show all commands
        /help analyze - Show detailed help for `analyze`
    """
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def aliases(self) -> List[str]:
        return ["h", "도움", "?"]
    
    @property
    def description(self) -> str:
        return "Show help information"
    
    @property
    def usage(self) -> str:
        return "/help [command]"
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute help command."""
        # Lazy import to avoid circular dependency
        from bot.dispatcher import get_dispatcher
        
        dispatcher = get_dispatcher()
        
        # Show detailed help for one command
        if args:
            cmd_name = args[0]
            command = dispatcher.get_command(cmd_name)
            
            if command is None:
                return BotResponse.error_response(f"알 수 없는 명령어: {cmd_name}")
            
            # Build detailed help text
            help_text = self._format_command_help(command, dispatcher.command_prefix)
            return BotResponse.markdown_response(help_text)
        
        # Show command list
        commands = dispatcher.list_commands(include_hidden=False)
        prefix = dispatcher.command_prefix
        
        help_text = self._format_help_list(commands, prefix)
        return BotResponse.markdown_response(help_text)
    
    def _format_help_list(self, commands: List[BotCommand], prefix: str) -> str:
        """Format command list."""
        lines = [
            "📚 **주식 분석 도우미 - 명령어 안내**",
            "",
            "사용 가능한 명령어:",
            "",
        ]
        
        for cmd in commands:
            # Command name and aliases
            aliases_str = ""
            if cmd.aliases:
                ascii_aliases = [a for a in cmd.aliases if a.isascii()]
                if ascii_aliases:
                    aliases_str = f" ({', '.join(prefix + a for a in ascii_aliases[:2])})"
            
            lines.append(f"• {prefix}{cmd.name}{aliases_str} - {cmd.description}")
            lines.append("")

        lines.extend([
            "",
            "---",
            f"💡 {prefix}help <명령어> 로 상세 사용법을 확인하세요.",
            "",
            "**예시:**",
            "",
            f"• {prefix}analyze 005930 - 삼성전자 분석",
            "",
            f"• {prefix}market - 시장 복기 실행",
            "",
            f"• {prefix}batch - 관심 종목 일괄 분석",
        ])
        
        return "\n".join(lines)
    
    def _format_command_help(self, command: BotCommand, prefix: str) -> str:
        """Format detailed help for a single command."""
        lines = [
            f"📖 **{prefix}{command.name}** - {command.description}",
            "",
            f"**사용법:** `{command.usage}`",
            "",
        ]
        
        # Aliases
        if command.aliases:
            aliases = [f"`{prefix}{a}`" if a.isascii() else f"`{a}`" for a in command.aliases]
            lines.append(f"**별칭:** {', '.join(aliases)}")
            lines.append("")
        
        # Permission
        if command.admin_only:
            lines.append("⚠️ **관리자 권한이 필요합니다.**")
            lines.append("")
        
        return "\n".join(lines)

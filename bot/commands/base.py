# -*- coding: utf-8 -*-
"""Abstract base class for bot command handlers."""

from abc import ABC, abstractmethod
from typing import List, Optional

from bot.models import BotMessage, BotResponse


class BotCommand(ABC):
    """
    Abstract base class for command handlers.

    All command handlers must inherit from this class and implement the abstract methods.

    Example:
        class MyCommand(BotCommand):
            @property
            def name(self) -> str:
                return "mycommand"
            
            @property
            def aliases(self) -> List[str]:
                return ["mc", "mycmd"]
            
            @property
            def description(self) -> str:
                return "Run my command"
            
            @property
            def usage(self) -> str:
                return "/mycommand [args]"
            
            def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
                return BotResponse.text_response("Command executed successfully")
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name without prefix, for example "analyze" for "/analyze"."""
        pass
    
    @property
    @abstractmethod
    def aliases(self) -> List[str]:
        """Command aliases, for example ["a", "분석"]."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description used in help output."""
        pass
    
    @property
    @abstractmethod
    def usage(self) -> str:
        """Usage text used in help output, for example "/analyze <stock_code>"."""
        pass
    
    @property
    def hidden(self) -> bool:
        """Whether this command is hidden from help output."""
        return False
    
    @property
    def admin_only(self) -> bool:
        """Whether this command requires admin privileges."""
        return False
    
    @abstractmethod
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the command."""
        pass
    
    def validate_args(self, args: List[str]) -> Optional[str]:
        """Validate parsed arguments and return an error message if invalid."""
        return None
    
    def get_help_text(self) -> str:
        """Return help text."""
        return f"**{self.name}** - {self.description}\n사용법: `{self.usage}`"

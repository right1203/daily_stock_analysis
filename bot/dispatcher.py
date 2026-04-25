# -*- coding: utf-8 -*-
"""Command dispatcher that parses, matches, and executes bot commands."""

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Type, Callable

from bot.models import BotMessage, BotResponse
from bot.commands.base import BotCommand

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple sliding-window rate limiter per user."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum request count within the window.
            window_seconds: Window size in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """Return whether the user is allowed to send a request."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove expired records.
        self._requests[user_id] = [
            t for t in self._requests[user_id] 
            if t > window_start
        ]
        
        # Check rate limit.
        if len(self._requests[user_id]) >= self.max_requests:
            return False
        
        # Record this request.
        self._requests[user_id].append(now)
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """Return remaining allowed requests."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove expired records.
        self._requests[user_id] = [
            t for t in self._requests[user_id] 
            if t > window_start
        ]
        
        return max(0, self.max_requests - len(self._requests[user_id]))


class CommandDispatcher:
    """
    Command dispatcher.

    Responsibilities:
    1. Register and manage command handlers.
    2. Parse commands and arguments from messages.
    3. Dispatch commands to matching handlers.
    4. Handle unknown commands and errors.

    Example:
        dispatcher = CommandDispatcher()
        dispatcher.register(AnalyzeCommand())
        dispatcher.register(HelpCommand())
        
        response = dispatcher.dispatch(message)
    """
    
    def __init__(
        self, 
        command_prefix: str = "/",
        rate_limit_requests: int = 10,
        rate_limit_window: int = 60,
        admin_users: Optional[List[str]] = None
    ):
        """
        Args:
            command_prefix: Command prefix, default "/".
            rate_limit_requests: Maximum request count within the rate-limit window.
            rate_limit_window: Rate-limit window size in seconds.
            admin_users: Admin user ID list.
        """
        self.command_prefix = command_prefix
        self.admin_users = set(admin_users or [])
        
        self._commands: Dict[str, BotCommand] = {}
        self._aliases: Dict[str, str] = {}
        self._rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        
        # Callback used by HelpCommand to get the command list.
        self._help_command_getter: Optional[Callable] = None
    
    def register(self, command: BotCommand) -> None:
        """Register a command instance."""
        name = command.name.lower()
        
        if name in self._commands:
            logger.warning("[Dispatcher] Command '%s' already exists and will be overwritten", name)
        
        self._commands[name] = command
        logger.debug("[Dispatcher] Registered command: %s", name)
        
        # Register aliases.
        for alias in command.aliases:
            alias_lower = alias.lower()
            if alias_lower in self._aliases:
                logger.warning("[Dispatcher] Alias '%s' already exists and will be overwritten", alias_lower)
            self._aliases[alias_lower] = name
            logger.debug("[Dispatcher] Registered alias: %s -> %s", alias_lower, name)
    
    def register_class(self, command_class: Type[BotCommand]) -> None:
        """Register a command class by instantiating it."""
        self.register(command_class())
    
    def unregister(self, name: str) -> bool:
        """Unregister a command by name."""
        name = name.lower()
        
        if name not in self._commands:
            return False
        
        command = self._commands.pop(name)
        
        # Remove aliases.
        for alias in command.aliases:
            self._aliases.pop(alias.lower(), None)
        
        logger.debug("[Dispatcher] Unregistered command: %s", name)
        return True
    
    def get_command(self, name: str) -> Optional[BotCommand]:
        """Return a command by name or alias."""
        name = name.lower()
        
        # Check command name first.
        if name in self._commands:
            return self._commands[name]
        
        # Then check aliases.
        if name in self._aliases:
            return self._commands.get(self._aliases[name])
        
        return None
    
    def list_commands(self, include_hidden: bool = False) -> List[BotCommand]:
        """List registered commands."""
        commands = list(self._commands.values())
        
        if not include_hidden:
            commands = [c for c in commands if not c.hidden]
        
        return sorted(commands, key=lambda c: c.name)
    
    def is_admin(self, user_id: str) -> bool:
        """Return whether the user is an admin."""
        return user_id in self.admin_users
    
    def add_admin(self, user_id: str) -> None:
        """Add an admin user."""
        self.admin_users.add(user_id)
    
    def remove_admin(self, user_id: str) -> None:
        """Remove an admin user."""
        self.admin_users.discard(user_id)
    
    def dispatch(self, message: BotMessage) -> BotResponse:
        """Dispatch a message to its matching command."""
        # 1. Check rate limit.
        if not self._rate_limiter.is_allowed(message.user_id):
            remaining_time = self._rate_limiter.window_seconds
            return BotResponse.error_response(
                f"요청이 너무 많습니다. {remaining_time}초 후 다시 시도해 주세요"
            )
        
        # 2. Parse command and arguments.
        cmd_name, args = message.get_command_and_args(self.command_prefix)
        
        if cmd_name is None:
            # Not a command; respond only when the bot was mentioned.
            if message.mentioned:
                return BotResponse.text_response(
                    "안녕하세요. 주식 분석 도우미입니다.\n"
                    f"`{self.command_prefix}help`를 보내 사용 가능한 명령을 확인하세요."
                )
            # Ignore non-command messages.
            return BotResponse.text_response("")
        
        logger.info("[Dispatcher] Received command: %s, args: %s, user: %s", cmd_name, args, message.user_name)
        
        # 3. Find command handler.
        command = self.get_command(cmd_name)
        
        if command is None:
            return BotResponse.error_response(
                f"알 수 없는 명령: {cmd_name}\n"
                f"`{self.command_prefix}help`를 보내 사용 가능한 명령을 확인하세요."
            )
        
        # 4. Check permissions.
        if command.admin_only and not self.is_admin(message.user_id):
            return BotResponse.error_response("이 명령은 관리자 권한이 필요합니다")
        
        # 5. Validate arguments.
        error_msg = command.validate_args(args)
        if error_msg:
            return BotResponse.error_response(
                f"{error_msg}\n사용법: `{command.usage}`"
            )
        
        # 6. Execute command.
        try:
            response = command.execute(message, args)
            logger.info("[Dispatcher] Command %s executed successfully", cmd_name)
            return response
        except Exception as e:
            logger.error("[Dispatcher] Command %s execution failed: %s", cmd_name, e)
            logger.exception(e)
            return BotResponse.error_response(f"명령 실행에 실패했습니다: {str(e)[:100]}")
    
    def set_help_command_getter(self, getter: Callable) -> None:
        """Set the command-list callback used by HelpCommand."""
        self._help_command_getter = getter


# Global dispatcher instance.
_dispatcher: Optional[CommandDispatcher] = None


def get_dispatcher() -> CommandDispatcher:
    """Return the global dispatcher, initializing and registering commands on first use."""
    global _dispatcher
    
    if _dispatcher is None:
        from src.config import get_config
        
        config = get_config()
        
        # Create dispatcher.
        _dispatcher = CommandDispatcher(
            command_prefix=getattr(config, 'bot_command_prefix', '/'),
            rate_limit_requests=getattr(config, 'bot_rate_limit_requests', 10),
            rate_limit_window=getattr(config, 'bot_rate_limit_window', 60),
            admin_users=getattr(config, 'bot_admin_users', []),
        )
        
        # Register all commands automatically.
        from bot.commands import ALL_COMMANDS
        for command_class in ALL_COMMANDS:
            _dispatcher.register_class(command_class)
        
        logger.info("[Dispatcher] Initialized with %d registered commands", len(_dispatcher._commands))
    
    return _dispatcher


def reset_dispatcher() -> None:
    """Reset the global dispatcher, mainly for tests."""
    global _dispatcher
    _dispatcher = None

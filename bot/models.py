# -*- coding: utf-8 -*-
"""
===================================
Bot message models
===================================

Defines common message and response models across retained bot platforms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class ChatType(str, Enum):
    """Chat type."""
    GROUP = "group"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class Platform(str, Enum):
    """Platform type."""
    TELEGRAM = "telegram"
    UNKNOWN = "unknown"


@dataclass
class BotMessage:
    """
    Common bot message model.

    Platform-specific message payloads are normalized into this model before
    command handlers process them.

    Attributes:
        platform: Platform identifier.
        message_id: Message ID from the platform.
        user_id: Sender ID.
        user_name: Sender display name.
        chat_id: Chat ID, such as group or private chat ID.
        chat_type: Chat type.
        content: Message text with bot mentions removed.
        raw_content: Original message content.
        mentioned: Whether the bot was mentioned.
        mentions: Mentioned user list.
        timestamp: Message timestamp.
        raw_data: Platform-specific raw payload for debugging.
    """
    platform: str
    message_id: str
    user_id: str
    user_name: str
    chat_id: str
    chat_type: ChatType
    content: str
    raw_content: str = ""
    mentioned: bool = False
    mentions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_command_and_args(self, prefix: str = "/") -> tuple:
        """
        Parse command and arguments.

        Args:
            prefix: Command prefix. Defaults to "/".

        Returns:
            (command, args), such as ("analyze", ["005930"]). Returns
            (None, []) when the message is not a command.
        """
        text = self.content.strip()

        # Only prefixed slash commands are accepted.
        if not text.startswith(prefix):
            return None, []

        # Remove prefix.
        text = text[len(prefix):]

        # Split command and arguments.
        parts = text.split()
        if not parts:
            return None, []
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    def is_command(self, prefix: str = "/") -> bool:
        """Return whether the message is a command."""
        cmd, _ = self.get_command_and_args(prefix)
        return cmd is not None


@dataclass
class BotResponse:
    """
    Common bot response model.

    Command handlers return this model, then platform adapters convert it into
    platform-specific response payloads.

    Attributes:
        text: Reply text.
        markdown: Whether the text is Markdown.
        at_user: Whether to mention the sender.
        reply_to_message: Whether to reply to the original message.
        extra: Platform-specific extra data.
    """
    text: str
    markdown: bool = False
    at_user: bool = True
    reply_to_message: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def text_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """Create a plain-text response."""
        return cls(text=text, markdown=False, at_user=at_user)
    
    @classmethod
    def markdown_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """Create a Markdown response."""
        return cls(text=text, markdown=True, at_user=at_user)
    
    @classmethod
    def error_response(cls, message: str) -> 'BotResponse':
        """Create an error response."""
        return cls(text=f"❌ 오류: {message}", markdown=False, at_user=True)


@dataclass
class WebhookResponse:
    """
    Webhook response model.

    Platform adapters return this model with HTTP response content.

    Attributes:
        status_code: HTTP status code.
        body: Response body serialized as JSON.
        headers: Extra response headers.
    """
    status_code: int = 200
    body: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def success(cls, body: Optional[Dict] = None) -> 'WebhookResponse':
        """Create a success response."""
        return cls(status_code=200, body=body or {})
    
    @classmethod
    def challenge(cls, challenge: str) -> 'WebhookResponse':
        """Create a challenge response for platform URL verification."""
        return cls(status_code=200, body={"challenge": challenge})
    
    @classmethod
    def error(cls, message: str, status_code: int = 400) -> 'WebhookResponse':
        """Create an error response."""
        return cls(status_code=status_code, body={"error": message})

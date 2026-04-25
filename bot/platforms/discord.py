# -*- coding: utf-8 -*-
"""Discord platform adapter."""

import logging
from typing import Dict, Any, Optional

from bot.platforms.base import BotPlatform
from bot.models import BotMessage, WebhookResponse


logger = logging.getLogger(__name__)


class DiscordPlatform(BotPlatform):
    """Discord platform adapter."""
    
    @property
    def platform_name(self) -> str:
        """Platform identifier."""
        return "discord"
    
    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify the Discord webhook request signature.
        
        Args:
            headers: HTTP request headers.
            body: Raw request body bytes.
            
        Returns:
            Whether the signature is valid.
        """
        # TODO: Implement Discord webhook signature verification.
        # This currently returns True and should be hardened later.
        return True
    
    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """Parse a Discord message into the unified format.
        
        Args:
            data: Parsed JSON data.
            
        Returns:
            BotMessage object, or None if no handling is needed.
        """
        # Check whether this is a message event.
        if data.get("type") != 1 and data.get("type") != 2:
            return None
        
        # Extract message content.
        content = data.get("content", "").strip()
        if not content:
            return None
        
        # Extract user info.
        author = data.get("author", {})
        user_id = author.get("id", "")
        user_name = author.get("username", "unknown")
        
        # Extract channel info.
        channel_id = data.get("channel_id", "")
        guild_id = data.get("guild_id", "")
        
        # Extract message ID.
        message_id = data.get("id", "")
        
        # Extract attachments if present.
        attachments = data.get("attachments", [])
        attachment_urls = [att["url"] for att in attachments if "url" in att]
        
        # Build BotMessage.
        message = BotMessage(
            platform="discord",
            message_id=message_id,
            user_id=user_id,
            user_name=user_name,
            content=content,
            attachment_urls=attachment_urls,
            channel_id=channel_id,
            group_id=guild_id,
            # Extract additional fields from Discord data.
            timestamp=data.get("timestamp"),
            mention_everyone=data.get("mention_everyone", False),
            mentions=data.get("mentions", []),
            
            # Add Discord-specific raw data.
            raw_data={
                "message_id": message_id,
                "channel_id": channel_id,
                "guild_id": guild_id,
                "author": author,
                "content": content,
                "timestamp": data.get("timestamp"),
                "attachments": attachments,
                "mentions": data.get("mentions", []),
                "mention_roles": data.get("mention_roles", []),
                "mention_everyone": data.get("mention_everyone", False),
                "type": data.get("type"),
            }
        )
        
        return message
    
    def format_response(self, response: Any, message: BotMessage) -> WebhookResponse:
        """Convert a unified response into Discord format.
        
        Args:
            response: Unified response object.
            message: Original message object.
            
        Returns:
            WebhookResponse object.
        """
        # Build Discord response format.
        discord_response = {
            "content": response.text if hasattr(response, "text") else str(response),
            "tts": False,
            "embeds": [],
            "allowed_mentions": {
                "parse": ["users", "roles", "everyone"]
            }
        }
        
        return WebhookResponse.success(discord_response)
    
    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """Handle Discord verification requests.
        
        Args:
            data: Request data.
            
        Returns:
            Verification response, or None if this is not a verification request.
        """
        # Discord webhook verification request type is 1.
        if data.get("type") == 1:
            return WebhookResponse.success({
                "type": 1
            })
        
        # Discord command interaction verification.
        if "challenge" in data:
            return WebhookResponse.success({
                "challenge": data["challenge"]
            })
        
        return None

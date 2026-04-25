# -*- coding: utf-8 -*-
"""
===================================
Bot Webhook Handler
===================================

Handle platform webhooks and dispatch parsed messages to command handlers.
"""

import json
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from bot.models import WebhookResponse
from bot.dispatcher import get_dispatcher
from bot.platforms import ALL_PLATFORMS

if TYPE_CHECKING:
    from bot.platforms.base import BotPlatform

logger = logging.getLogger(__name__)

# Platform instance cache
_platform_instances: Dict[str, 'BotPlatform'] = {}


def get_platform(platform_name: str) -> Optional['BotPlatform']:
    """
    Get a platform adapter instance.
    
    Args:
        platform_name: Platform name
        
    Returns:
        Platform adapter instance, or None.
    """
    if platform_name not in _platform_instances:
        platform_class = ALL_PLATFORMS.get(platform_name)
        if platform_class:
            _platform_instances[platform_name] = platform_class()
        else:
            logger.warning(f"[BotHandler] Unknown platform: {platform_name}")
            return None
    
    return _platform_instances[platform_name]


def handle_webhook(
    platform_name: str,
    headers: Dict[str, str],
    body: bytes,
    query_params: Optional[Dict[str, list]] = None
) -> WebhookResponse:
    """
    Handle a webhook request.

    This is the unified entry point for all platform webhooks.
    
    Args:
        platform_name: Platform name (feishu, dingtalk, wecom, telegram)
        headers: HTTP request headers
        body: Raw request body bytes
        query_params: URL query parameters (used by some platform validations)
        
    Returns:
        WebhookResponse object.
    """
    logger.info(f"[BotHandler] Received {platform_name} webhook request")
    
    # Check whether bot mode is enabled
    from src.config import get_config
    config = get_config()
    
    if not getattr(config, 'bot_enabled', True):
        logger.info("[BotHandler] Bot mode is disabled")
        return WebhookResponse.success()
    
    # Resolve platform adapter
    platform = get_platform(platform_name)
    if not platform:
        return WebhookResponse.error(f"Unknown platform: {platform_name}", 400)
    
    # Parse JSON payload
    try:
        data = json.loads(body.decode('utf-8')) if body else {}
    except json.JSONDecodeError as e:
        logger.error(f"[BotHandler] JSON parse failed: {e}")
        return WebhookResponse.error("Invalid JSON", 400)
    
    logger.debug(f"[BotHandler] Request payload: {json.dumps(data, ensure_ascii=False)[:500]}")
    
    # Parse webhook message
    message, challenge_response = platform.handle_webhook(headers, body, data)
    
    # Return challenge response for URL verification
    if challenge_response:
        logger.info("[BotHandler] Returning challenge response")
        return challenge_response
    
    # Return success if no actionable message exists
    if not message:
        logger.debug("[BotHandler] No actionable message")
        return WebhookResponse.success()
    
    logger.info(f"[BotHandler] Parsed message: user={message.user_name}, content={message.content[:50]}")
    
    # Dispatch to command handler
    dispatcher = get_dispatcher()
    response = dispatcher.dispatch(message)
    
    # Format platform-specific response
    if response.text:
        webhook_response = platform.format_response(response, message)
        return webhook_response
    
    return WebhookResponse.success()


def handle_feishu_webhook(headers: Dict[str, str], body: bytes) -> WebhookResponse:
    """Handle Feishu webhook."""
    return handle_webhook('feishu', headers, body)


def handle_dingtalk_webhook(headers: Dict[str, str], body: bytes) -> WebhookResponse:
    """Handle DingTalk webhook."""
    return handle_webhook('dingtalk', headers, body)


def handle_wecom_webhook(headers: Dict[str, str], body: bytes) -> WebhookResponse:
    """Handle WeCom webhook."""
    return handle_webhook('wecom', headers, body)


def handle_telegram_webhook(headers: Dict[str, str], body: bytes) -> WebhookResponse:
    """处理 Telegram Webhook"""
    return handle_webhook('telegram', headers, body)

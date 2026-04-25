# -*- coding: utf-8 -*-
"""
===================================
Bot command trigger system
===================================

Provides stock analysis and market review commands through retained bot
platforms such as Telegram and Discord.

Module layout:
- models.py: shared message and response models
- dispatcher.py: command dispatcher
- commands/: command handlers
- platforms/: platform adapters
- handler.py: webhook handler

Usage:
1. Configure the token and webhook settings for the retained platform.
2. Start the WebUI/API service.
3. Register the platform webhook URL, for example:
   - Telegram: http://your-server/bot/telegram
   - Discord: http://your-server/bot/discord

Supported commands:
- /analyze <stock_code> - analyze a stock
- /market               - generate a market review
- /batch                - analyze configured watchlist stocks
- /help                 - show help
- /status               - show system status
"""

from bot.models import BotMessage, BotResponse, ChatType, WebhookResponse
from bot.dispatcher import CommandDispatcher, get_dispatcher

__all__ = [
    'BotMessage',
    'BotResponse',
    'ChatType',
    'WebhookResponse',
    'CommandDispatcher',
    'get_dispatcher',
]

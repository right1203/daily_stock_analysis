# -*- coding: utf-8 -*-
"""
===================================
Platform Adapter Module
===================================

Contains supported platform webhook handling and message parsing adapters.
"""

from bot.platforms.base import BotPlatform

# Available webhook platforms.
ALL_PLATFORMS = {
}

__all__ = [
    'BotPlatform',
    'ALL_PLATFORMS',
]

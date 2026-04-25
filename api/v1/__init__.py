# -*- coding: utf-8 -*-
"""
===================================
API v1 Module Initialization
===================================

Responsibilities:
1. Export API v1 routers
"""

from api.v1.router import router as api_v1_router

__all__ = ["api_v1_router"]

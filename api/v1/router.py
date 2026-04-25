# -*- coding: utf-8 -*-
"""
===================================
API v1 Router Aggregation
===================================

Responsibilities:
1. Aggregate all endpoint routers for API v1
2. Apply the shared /api/v1 prefix
"""

from fastapi import APIRouter

from api.v1.endpoints import analysis, auth, history, stocks, backtest, system_config, agent

# Main API v1 router
router = APIRouter(prefix="/api/v1")

router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)

router.include_router(
    agent.router,
    prefix="/agent",
    tags=["Agent"]
)

router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"]
)

router.include_router(
    history.router,
    prefix="/history",
    tags=["History"]
)

router.include_router(
    stocks.router,
    prefix="/stocks",
    tags=["Stocks"]
)

router.include_router(
    backtest.router,
    prefix="/backtest",
    tags=["Backtest"]
)

router.include_router(
    system_config.router,
    prefix="/system",
    tags=["SystemConfig"]
)

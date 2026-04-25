# -*- coding: utf-8 -*-
"""
Market recap profile configuration.

Defines per-region metadata such as indices, news queries, and prompt hints.
MarketAnalyzer uses these profiles to switch between KR and US behavior.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class MarketProfile:
    """Market recap profile settings."""

    region: str  # "kr" | "us"
    # Index code used to classify the broad market trend.
    mood_index_code: str
    # News search queries.
    news_queries: List[str]
    # Prompt hint for index analysis.
    prompt_index_hint: str
    # Whether market breadth statistics are available.
    has_market_stats: bool
    # Whether sector rankings are available.
    has_sector_rankings: bool


KR_PROFILE = MarketProfile(
    region="kr",
    mood_index_code="KOSPI",
    news_queries=[
        "코스피 코스닥 시장 동향",
        "한국 증시 분석",
        "한국 주식시장 주요 테마",
    ],
    prompt_index_hint="코스피, 코스닥 등 각 지수의 추세 특징을 분석하세요",
    has_market_stats=True,
    has_sector_rankings=True,
)

US_PROFILE = MarketProfile(
    region="us",
    mood_index_code="SPX",
    news_queries=[
        "US stock market today",
        "S&P 500 NASDAQ analysis",
        "Wall Street market recap",
    ],
    prompt_index_hint="S&P 500, NASDAQ, Dow Jones 등 각 지수의 추세 특징을 분석하세요",
    has_market_stats=False,
    has_sector_rankings=False,
)


def get_profile(region: str) -> MarketProfile:
    """Return the market profile for a region."""
    if region == "us":
        return US_PROFILE
    return KR_PROFILE

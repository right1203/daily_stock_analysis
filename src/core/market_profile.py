# -*- coding: utf-8 -*-
"""
대시보드 복기 시장 영역 설정

각 시장 영역의 지수, 뉴스 검색어, 프롬프트 힌트 등 메타데이터를 정의합니다.
MarketAnalyzer에서 region에 따라 한국/미국 복기 동작을 전환합니다.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class MarketProfile:
    """대시보드 복기 시장 영역 설정"""

    region: str  # "kr" | "us"
    # 전체 추세 판단에 사용할 지수 코드
    mood_index_code: str
    # 뉴스 검색 키워드
    news_queries: List[str]
    # 지수 분석 프롬프트 힌트
    prompt_index_hint: str
    # 시장 개요에 상승/하락 종목 수, 상한가/하한가 포함 여부
    has_market_stats: bool
    # 시장 개요에 업종별 등락 포함 여부
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
    """region에 따라 해당 MarketProfile을 반환합니다"""
    if region == "us":
        return US_PROFILE
    return KR_PROFILE

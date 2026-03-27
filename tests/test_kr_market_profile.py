# tests/test_kr_market_profile.py
# -*- coding: utf-8 -*-
"""Tests for Korean market profile and strategy blueprint."""

import pytest
from src.core.market_profile import get_profile, KR_PROFILE, US_PROFILE
from src.core.market_strategy import get_market_strategy_blueprint, KR_BLUEPRINT


class TestKrProfile:
    def test_kr_profile_exists(self):
        assert KR_PROFILE is not None
        assert KR_PROFILE.region == "kr"

    def test_kr_mood_index(self):
        assert KR_PROFILE.mood_index_code == "KOSPI"

    def test_kr_news_queries_korean(self):
        for query in KR_PROFILE.news_queries:
            assert isinstance(query, str)
            assert len(query) > 0

    def test_kr_has_market_stats(self):
        assert KR_PROFILE.has_market_stats is True

    def test_kr_has_sector_rankings(self):
        assert KR_PROFILE.has_sector_rankings is True

    def test_get_profile_kr(self):
        profile = get_profile("kr")
        assert profile.region == "kr"

    def test_get_profile_us(self):
        profile = get_profile("us")
        assert profile.region == "us"

    def test_get_profile_default(self):
        profile = get_profile("unknown")
        assert profile.region == "kr"


class TestUsProfile:
    def test_us_profile_region(self):
        assert US_PROFILE.region == "us"

    def test_us_mood_index(self):
        assert US_PROFILE.mood_index_code == "SPX"


class TestKrBlueprint:
    def test_kr_blueprint_exists(self):
        assert KR_BLUEPRINT is not None
        assert KR_BLUEPRINT.region == "kr"

    def test_kr_blueprint_has_dimensions(self):
        assert len(KR_BLUEPRINT.dimensions) >= 3

    def test_kr_blueprint_to_prompt(self):
        prompt = KR_BLUEPRINT.to_prompt_block()
        assert "Strategy Blueprint" in prompt

    def test_kr_blueprint_to_markdown(self):
        md = KR_BLUEPRINT.to_markdown_block()
        assert "전략 프레임워크" in md

    def test_get_blueprint_kr(self):
        bp = get_market_strategy_blueprint("kr")
        assert bp.region == "kr"

    def test_get_blueprint_us(self):
        bp = get_market_strategy_blueprint("us")
        assert bp.region == "us"

    def test_get_blueprint_default(self):
        bp = get_market_strategy_blueprint("unknown")
        assert bp.region == "kr"

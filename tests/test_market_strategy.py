# -*- coding: utf-8 -*-
"""Tests for market strategy blueprints."""

import unittest

from src.core.market_strategy import get_market_strategy_blueprint
from src.market_analyzer import MarketAnalyzer, MarketOverview


class TestMarketStrategyBlueprint(unittest.TestCase):
    """Validate KR/US strategy blueprint basics."""

    def test_kr_blueprint_contains_action_framework(self):
        blueprint = get_market_strategy_blueprint("kr")
        block = blueprint.to_prompt_block()

        self.assertIn("한국 시장 3단계 복기 전략", block)
        self.assertIn("실행 프레임워크", block)
        self.assertIn("공격", block)

    def test_us_blueprint_contains_regime_strategy(self):
        blueprint = get_market_strategy_blueprint("us")
        block = blueprint.to_prompt_block()

        self.assertIn("미국 시장 국면 전략", block)
        self.assertIn("리스크온", block)
        self.assertIn("매크로와 자금 흐름", block)


class TestMarketAnalyzerStrategyPrompt(unittest.TestCase):
    """Validate strategy section is injected into prompt/report."""

    def test_default_region_is_kr(self):
        analyzer = MarketAnalyzer()

        self.assertEqual(analyzer.region, "kr")

    def test_invalid_region_falls_back_to_kr(self):
        analyzer = MarketAnalyzer(region="legacy")

        self.assertEqual(analyzer.region, "kr")

    def test_kr_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="kr")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("전략 계획", prompt)
        self.assertIn("한국 시장 3단계 복기 전략", prompt)
        self.assertNotIn("A/H", prompt)
        self.assertNotIn("KR/US stock", prompt)

    def test_us_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="us")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("전략 계획", prompt)
        self.assertIn("미국 시장 국면 전략", prompt)
        self.assertNotIn("A/H", prompt)
        self.assertNotIn("A-share", prompt)  # kr-us-static-allow: removed-market


if __name__ == "__main__":
    unittest.main()

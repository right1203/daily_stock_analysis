# tests/test_kr_trading_calendar.py
# -*- coding: utf-8 -*-
"""Tests for KRX trading calendar integration."""

import os
import sys
from unittest.mock import MagicMock, patch

# Provide lightweight stubs so importing trading_calendar does not require
# full LLM/HTTP runtime dependencies in minimal CI.
for _mod in ("litellm", "json_repair", "dotenv", "openai", "anthropic", "requests",
             "fake_useragent", "efinance"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Import helper functions directly from the lightweight submodule files,
# bypassing data_provider/__init__.py which pulls in heavy optional deps.
_DP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data_provider"))
sys.path.insert(0, _DP_DIR)

from us_index_mapping import is_us_index_code, is_us_stock_code  # noqa: E402
from kr_index_mapping import is_kr_index_code, is_kr_stock_code  # noqa: E402

import pytest  # noqa: E402
from src.core.trading_calendar import (  # noqa: E402
    MARKET_EXCHANGE,
    MARKET_TIMEZONE,
    get_market_for_stock,
    compute_effective_region,
)


def _call_get_market(code: str):
    """Call get_market_for_stock with real helper functions patched in."""
    with (
        patch("data_provider.is_us_stock_code", side_effect=is_us_stock_code),
        patch("data_provider.is_us_index_code", side_effect=is_us_index_code),
        patch(
            "data_provider.kr_index_mapping.is_kr_index_code",
            side_effect=is_kr_index_code,
        ),
        patch(
            "data_provider.kr_index_mapping.is_kr_stock_code",
            side_effect=is_kr_stock_code,
        ),
    ):
        return get_market_for_stock(code)


class TestMarketExchange:
    def test_kr_exchange_exists(self):
        assert "kr" in MARKET_EXCHANGE
        assert MARKET_EXCHANGE["kr"] == "XKRX"

    def test_us_exchange_exists(self):
        assert "us" in MARKET_EXCHANGE
        assert MARKET_EXCHANGE["us"] == "XNYS"

    def test_cn_exchange_removed(self):
        assert "cn" not in MARKET_EXCHANGE

    def test_hk_exchange_removed(self):
        assert "hk" not in MARKET_EXCHANGE


class TestMarketTimezone:
    def test_kr_timezone(self):
        assert MARKET_TIMEZONE["kr"] == "Asia/Seoul"

    def test_us_timezone(self):
        assert MARKET_TIMEZONE["us"] == "America/New_York"


class TestGetMarketForStock:
    def test_kr_stock(self):
        assert _call_get_market("005930") == "kr"

    def test_us_stock(self):
        assert _call_get_market("AAPL") == "us"

    def test_us_index(self):
        assert _call_get_market("SPX") == "us"

    def test_kr_index(self):
        assert _call_get_market("KOSPI") == "kr"

    def test_empty_string(self):
        assert get_market_for_stock("") is None

    def test_none(self):
        assert get_market_for_stock(None) is None


class TestComputeEffectiveRegion:
    def test_kr_open(self):
        assert compute_effective_region("kr", {"kr", "us"}) == "kr"

    def test_kr_closed(self):
        assert compute_effective_region("kr", {"us"}) == ""

    def test_us_open(self):
        assert compute_effective_region("us", {"kr", "us"}) == "us"

    def test_us_closed(self):
        assert compute_effective_region("us", {"kr"}) == ""

    def test_both_all_open(self):
        assert compute_effective_region("both", {"kr", "us"}) == "both"

    def test_both_only_kr(self):
        assert compute_effective_region("both", {"kr"}) == "kr"

    def test_both_only_us(self):
        assert compute_effective_region("both", {"us"}) == "us"

    def test_both_none_open(self):
        assert compute_effective_region("both", set()) == ""

    def test_invalid_region_defaults_to_kr(self):
        assert compute_effective_region("cn", {"kr", "us"}) == "kr"

    def test_invalid_region_xyz(self):
        assert compute_effective_region("xyz", {"kr"}) == "kr"

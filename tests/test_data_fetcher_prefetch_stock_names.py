# -*- coding: utf-8 -*-
"""
Regression tests for stock-name prefetch behavior.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, call

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_provider.base import DataFetchError, DataFetcherManager


def test_fetcher_manager_uses_kr_us_fetchers_only():
    manager = DataFetcherManager()

    assert manager.available_fetchers == ["pykrx", "YfinanceFetcher"]


class _DummyFetcher:
    name = "DummyFetcher"

    @staticmethod
    def get_stock_name(_stock_code):
        return "테스트 종목"


class _FailingPykrxFetcher:
    name = "pykrx"
    priority = 0

    def __init__(self):
        self.received_codes = []

    @staticmethod
    def supports(stock_code):
        return stock_code.isdigit()

    def get_daily_data(self, stock_code, **_kwargs):
        self.received_codes.append(stock_code)
        raise DataFetchError("pykrx unavailable")


class _CapturingYfinanceFetcher:
    name = "YfinanceFetcher"
    priority = 1

    def __init__(self):
        self.received_codes = []

    @staticmethod
    def supports(_stock_code):
        return True

    def get_daily_data(self, stock_code, **_kwargs):
        self.received_codes.append(stock_code)
        return pd.DataFrame({"date": ["2024-01-02"], "close": [100.0]})


def test_explicit_kosdaq_suffix_is_preserved_for_yfinance_fallback():
    pykrx_fetcher = _FailingPykrxFetcher()
    yfinance_fetcher = _CapturingYfinanceFetcher()
    manager = DataFetcherManager(fetchers=[pykrx_fetcher, yfinance_fetcher])

    _, provider_name = manager.get_daily_data("091990.KQ", start_date="2024-01-01", end_date="2024-01-03")

    assert provider_name == "YfinanceFetcher"
    assert pykrx_fetcher.received_codes == ["091990"]
    assert yfinance_fetcher.received_codes == ["091990.KQ"]


class TestPrefetchStockNames(unittest.TestCase):
    def test_prefetch_stock_names_calls_get_stock_name_without_realtime(self):
        manager = DataFetcherManager.__new__(DataFetcherManager)
        manager.get_stock_name = MagicMock(return_value="")

        DataFetcherManager.prefetch_stock_names(manager, ["KR005930", "000660"], use_bulk=False)

        manager.get_stock_name.assert_has_calls(
            [
                call("005930", allow_realtime=False),
                call("000660", allow_realtime=False),
            ]
        )

    def test_get_stock_name_skips_realtime_when_allow_realtime_false(self):
        manager = DataFetcherManager.__new__(DataFetcherManager)
        manager._fetchers = [_DummyFetcher()]
        manager.get_realtime_quote = MagicMock(return_value=MagicMock(name="실시간 이름"))

        name = DataFetcherManager.get_stock_name(manager, "123456", allow_realtime=False)

        self.assertEqual(name, "테스트 종목")
        manager.get_realtime_quote.assert_not_called()


if __name__ == "__main__":
    unittest.main()

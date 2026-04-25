# -*- coding: utf-8 -*-
"""
Unit tests for US index fetching in data_provider/yfinance_fetcher

Covers yfinance API responses with unittest.mock:
- _fetch_yf_ticker_data single-index parsing
- _get_us_main_indices batch fetching and error handling
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Mock optional dependencies before importing data_provider so env differences do not break tests
if 'fake_useragent' not in sys.modules:
    sys.modules['fake_useragent'] = MagicMock()

# Ensure project modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def _make_mock_hist(close: float, prev_close: float, high: float = None, low: float = None) -> pd.DataFrame:
    """Build a mock history DataFrame with fields needed for change percentage"""
    high = high if high is not None else close + 1
    low = low if low is not None else close - 1
    return pd.DataFrame({
        'Close': [prev_close, close],
        'Open': [prev_close - 0.5, close - 0.3],
        'High': [prev_close + 1, high],
        'Low': [prev_close - 1, low],
        'Volume': [1000000.0, 1200000.0],
    }, index=pd.DatetimeIndex(['2025-02-16', '2025-02-17']))


def _make_mock_yf(hist_df: pd.DataFrame):
    """Build a mock yf module where Ticker().history() returns the given DataFrame"""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = hist_df
    mock_yf = MagicMock()
    mock_yf.Ticker.return_value = mock_ticker
    return mock_yf


class TestFetchYfTickerData(unittest.TestCase):
    """Tests for _fetch_yf_ticker_data single-index fetching"""

    def setUp(self):
        from data_provider.yfinance_fetcher import YfinanceFetcher
        self.fetcher = YfinanceFetcher()

    def test_returns_dict_with_correct_fields(self):
        """Valid data should return a dict with code, name, current, and change_pct"""
        mock_hist = _make_mock_hist(close=5100.0, prev_close=5000.0)
        mock_yf = _make_mock_yf(mock_hist)

        result = self.fetcher._fetch_yf_ticker_data(mock_yf, '^GSPC', 'S&P 500 Index', 'SPX')

        self.assertIsNotNone(result)
        self.assertEqual(result['code'], 'SPX')
        self.assertEqual(result['name'], 'S&P 500 Index')
        self.assertEqual(result['current'], 5100.0)
        self.assertEqual(result['prev_close'], 5000.0)
        self.assertEqual(result['change'], 100.0)
        self.assertAlmostEqual(result['change_pct'], 2.0)
        self.assertIn('open', result)
        self.assertIn('high', result)
        self.assertIn('low', result)
        self.assertIn('volume', result)
        self.assertIn('amount', result)
        self.assertIn('amplitude', result)

    def test_returns_none_when_history_empty(self):
        """Empty history should return None"""
        mock_yf = _make_mock_yf(pd.DataFrame())

        result = self.fetcher._fetch_yf_ticker_data(mock_yf, '^GSPC', 'S&P 500 Index', 'SPX')

        self.assertIsNone(result)

    def test_single_row_history_uses_same_as_prev(self):
        """Single-row history should use current as prev_close and change_pct 0"""
        mock_hist = _make_mock_hist(close=5000.0, prev_close=5000.0)
        mock_hist = mock_hist.iloc[[-1]]
        mock_yf = _make_mock_yf(mock_hist)

        result = self.fetcher._fetch_yf_ticker_data(mock_yf, '^GSPC', 'S&P 500 Index', 'SPX')

        self.assertIsNotNone(result)
        self.assertEqual(result['change_pct'], 0.0)


class TestGetUsMainIndices(unittest.TestCase):
    """Tests for _get_us_main_indices batch fetching"""

    def setUp(self):
        from data_provider.yfinance_fetcher import YfinanceFetcher
        self.fetcher = YfinanceFetcher()

    @patch('data_provider.yfinance_fetcher.get_us_index_yf_symbol')
    def test_returns_list_when_mock_succeeds(self, mock_get_symbol):
        """Successful mapping and fetching should return an index list"""
        def get_symbol(code):
            mapping = {
                'SPX': ('^GSPC', 'S&P 500 Index'),
                'IXIC': ('^IXIC', 'NASDAQ Composite'),
                'DJI': ('^DJI', 'Dow Jones Industrial Average'),
                'VIX': ('^VIX', 'VIX Volatility Index'),
            }
            return mapping.get(code, (None, None))

        mock_get_symbol.side_effect = get_symbol
        mock_hist = _make_mock_hist(close=5100.0, prev_close=5000.0)
        mock_yf = _make_mock_yf(mock_hist)

        result = self.fetcher._get_us_main_indices(mock_yf)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        for item in result:
            self.assertIn('code', item)
            self.assertIn('name', item)
            self.assertIn('current', item)
            self.assertIn('change_pct', item)

    @patch('data_provider.yfinance_fetcher.get_us_index_yf_symbol')
    def test_handles_empty_history_gracefully(self, mock_get_symbol):
        """Empty history for some indexes should still return fetched indexes"""
        call_count = [0]

        def get_symbol(code):
            return ('^GSPC', 'S&P 500 Index') if code == 'SPX' else (
                ('^IXIC', 'NASDAQ Composite') if code == 'IXIC' else (None, None)
            )

        def history_side_effect(period):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_mock_hist(close=5100.0, prev_close=5000.0)
            return pd.DataFrame()

        mock_get_symbol.side_effect = get_symbol
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = history_side_effect
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        result = self.fetcher._get_us_main_indices(mock_yf)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)

    @patch('data_provider.yfinance_fetcher.get_us_index_yf_symbol')
    def test_returns_none_when_all_fail(self, mock_get_symbol):
        """All fetch failures should return None"""
        mock_get_symbol.return_value = (None, None)
        mock_yf = _make_mock_yf(pd.DataFrame())

        result = self.fetcher._get_us_main_indices(mock_yf)

        self.assertIsNone(result)

    @patch('data_provider.yfinance_fetcher.get_us_index_yf_symbol')
    def test_handles_ticker_exception(self, mock_get_symbol):
        """Ticker.history exceptions should skip that index without failing all results"""
        mock_get_symbol.return_value = ('^GSPC', 'S&P 500 Index')
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("Network error")
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        result = self.fetcher._get_us_main_indices(mock_yf)

        self.assertIsNone(result)

    @patch('data_provider.yfinance_fetcher.get_us_index_yf_symbol')
    def test_skips_unknown_index_code(self, mock_get_symbol):
        """get_us_index_yf_symbol codes returning (None, None) should be skipped"""
        def get_symbol(code):
            if code == 'SPX':
                return ('^GSPC', 'S&P 500 Index')
            return (None, None)

        mock_get_symbol.side_effect = get_symbol
        mock_hist = _make_mock_hist(close=5100.0, prev_close=5000.0)
        mock_yf = _make_mock_yf(mock_hist)

        result = self.fetcher._get_us_main_indices(mock_yf)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['code'], 'SPX')


if __name__ == '__main__':
    unittest.main()

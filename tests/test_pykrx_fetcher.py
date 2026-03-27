# tests/test_pykrx_fetcher.py
# -*- coding: utf-8 -*-
"""Tests for PykrxFetcher."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from data_provider.pykrx_fetcher import PykrxFetcher, STANDARD_COLUMNS


class TestPykrxFetcherInit:
    def test_fetcher_name(self):
        fetcher = PykrxFetcher()
        assert fetcher.name == "pykrx"

    def test_default_priority(self):
        fetcher = PykrxFetcher()
        assert fetcher.priority == 0


class TestPykrxFetcherSupports:
    def test_supports_kr_stock(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("005930") is True

    def test_does_not_support_us_stock(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("AAPL") is False

    def test_does_not_support_kr_index(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("KOSPI") is False

    def test_does_not_support_empty(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("") is False

    def test_does_not_support_kosdaq_index(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("KOSDAQ") is False

    def test_supports_another_kr_stock(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("035720") is True


class TestPykrxFetcherFetchRawData:
    def test_returns_empty_df_when_pykrx_unavailable(self):
        fetcher = PykrxFetcher()
        import data_provider.pykrx_fetcher as module
        with patch.object(module, '_PYKRX_AVAILABLE', False):
            result = fetcher._fetch_raw_data("005930", "2024-01-01", "2024-01-31")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_fetch_raw_data_calls_pykrx_with_correct_format(self):
        fetcher = PykrxFetcher()
        import data_provider.pykrx_fetcher as module

        mock_df = pd.DataFrame(
            {
                '시가': [70000],
                '고가': [71000],
                '저가': [69000],
                '종가': [70500],
                '거래량': [1000000],
                '거래대금': [70500000000],
                '등락률': [0.71],
            },
            index=pd.to_datetime(['2024-01-02']),
        )
        mock_df.index.name = '날짜'

        with patch.object(module, '_PYKRX_AVAILABLE', True):
            mock_pykrx = MagicMock()
            mock_pykrx.get_market_ohlcv_by_date.return_value = mock_df
            with patch.object(module, 'pykrx_stock', mock_pykrx):
                result = fetcher._fetch_raw_data("005930", "2024-01-01", "2024-01-31")

        mock_pykrx.get_market_ohlcv_by_date.assert_called_once_with(
            "20240101", "20240131", "005930"
        )
        assert not result.empty

    def test_fetch_raw_data_returns_empty_df_when_pykrx_returns_none(self):
        fetcher = PykrxFetcher()
        import data_provider.pykrx_fetcher as module

        with patch.object(module, '_PYKRX_AVAILABLE', True):
            mock_pykrx = MagicMock()
            mock_pykrx.get_market_ohlcv_by_date.return_value = None
            with patch.object(module, 'pykrx_stock', mock_pykrx):
                result = fetcher._fetch_raw_data("005930", "2024-01-01", "2024-01-31")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestPykrxFetcherNormalizeData:
    def _make_pykrx_df(self):
        df = pd.DataFrame(
            {
                '시가': [70000, 71000],
                '고가': [71000, 72000],
                '저가': [69000, 70000],
                '종가': [70500, 71500],
                '거래량': [1000000, 1200000],
                '거래대금': [70500000000, 85800000000],
                '등락률': [0.71, 1.42],
            },
            index=pd.to_datetime(['2024-01-02', '2024-01-03']),
        )
        df.index.name = '날짜'
        return df

    def test_normalize_returns_standard_columns(self):
        fetcher = PykrxFetcher()
        raw = self._make_pykrx_df()
        result = fetcher._normalize_data(raw, "005930")
        assert list(result.columns) == STANDARD_COLUMNS

    def test_normalize_date_format(self):
        fetcher = PykrxFetcher()
        raw = self._make_pykrx_df()
        result = fetcher._normalize_data(raw, "005930")
        assert result['date'].iloc[0] == '2024-01-02'

    def test_normalize_values_correct(self):
        fetcher = PykrxFetcher()
        raw = self._make_pykrx_df()
        result = fetcher._normalize_data(raw, "005930")
        assert result['open'].iloc[0] == 70000
        assert result['close'].iloc[0] == 70500
        assert result['volume'].iloc[0] == 1000000
        assert result['pct_chg'].iloc[0] == pytest.approx(0.71)

    def test_normalize_row_count(self):
        fetcher = PykrxFetcher()
        raw = self._make_pykrx_df()
        result = fetcher._normalize_data(raw, "005930")
        assert len(result) == 2

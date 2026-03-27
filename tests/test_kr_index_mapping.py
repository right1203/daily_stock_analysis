# tests/test_kr_index_mapping.py
# -*- coding: utf-8 -*-
"""Tests for Korean index code mapping."""

import pytest
from data_provider.kr_index_mapping import (
    KR_INDEX_MAPPING,
    is_kr_index_code,
    is_kr_stock_code,
    get_kr_index_yf_symbol,
)


class TestIsKrIndexCode:
    def test_kospi_index(self):
        assert is_kr_index_code("KOSPI") is True

    def test_kosdaq_index(self):
        assert is_kr_index_code("KOSDAQ") is True

    def test_kospi200_index(self):
        assert is_kr_index_code("KS200") is True

    def test_case_insensitive(self):
        assert is_kr_index_code("kospi") is True

    def test_not_an_index(self):
        assert is_kr_index_code("005930") is False

    def test_us_stock_not_kr_index(self):
        assert is_kr_index_code("AAPL") is False

    def test_empty_string(self):
        assert is_kr_index_code("") is False

    def test_none(self):
        assert is_kr_index_code(None) is False


class TestIsKrStockCode:
    def test_kospi_stock(self):
        assert is_kr_stock_code("005930") is True  # Samsung

    def test_kosdaq_stock(self):
        assert is_kr_stock_code("035720") is True  # Kakao

    def test_us_ticker_not_kr(self):
        assert is_kr_stock_code("AAPL") is False

    def test_index_code_not_stock(self):
        assert is_kr_stock_code("KOSPI") is False

    def test_empty_string(self):
        assert is_kr_stock_code("") is False

    def test_five_digit_code(self):
        assert is_kr_stock_code("00593") is False

    def test_seven_digit_code(self):
        assert is_kr_stock_code("0059301") is False


class TestGetKrIndexYfSymbol:
    def test_kospi(self):
        symbol, name = get_kr_index_yf_symbol("KOSPI")
        assert symbol == "^KS11"
        assert "코스피" in name

    def test_kosdaq(self):
        symbol, name = get_kr_index_yf_symbol("KOSDAQ")
        assert symbol == "^KQ11"
        assert "코스닥" in name

    def test_not_found(self):
        assert get_kr_index_yf_symbol("AAPL") == (None, None)

    def test_case_insensitive(self):
        symbol, _ = get_kr_index_yf_symbol("kospi")
        assert symbol == "^KS11"

# tests/test_kr_stock_detection.py
# -*- coding: utf-8 -*-
"""Tests for Korean stock code detection and normalization."""

import sys
import unittest
from unittest.mock import MagicMock

# Provide lightweight stubs so importing data_provider.base does not require
# full LLM runtime dependencies in minimal CI.
if "litellm" not in sys.modules:
    sys.modules["litellm"] = MagicMock()
if "json_repair" not in sys.modules:
    sys.modules["json_repair"] = MagicMock()

# Core imports (should stay runnable even when optional data-source deps are absent)
try:
    from data_provider.base import normalize_stock_code, canonical_stock_code
    _BASE_IMPORTS_OK = True
    _BASE_IMPORT_ERROR = ""
except ImportError as e:
    _BASE_IMPORTS_OK = False
    _BASE_IMPORT_ERROR = str(e)


@unittest.skipIf(not _BASE_IMPORTS_OK, f"base imports failed: {_BASE_IMPORT_ERROR}")
class TestNormalizeKrStockCode(unittest.TestCase):
    """Tests for normalize_stock_code() Korean market support."""

    def test_plain_6digit(self):
        self.assertEqual(normalize_stock_code("005930"), "005930")

    def test_kr_prefix(self):
        self.assertEqual(normalize_stock_code("KR005930"), "005930")

    def test_kr_prefix_lowercase(self):
        self.assertEqual(normalize_stock_code("kr005930"), "005930")

    def test_dot_ks_suffix(self):
        self.assertEqual(normalize_stock_code("005930.KS"), "005930")

    def test_dot_kq_suffix(self):
        self.assertEqual(normalize_stock_code("035720.KQ"), "035720")

    def test_us_stock_unchanged(self):
        self.assertEqual(normalize_stock_code("AAPL"), "AAPL")

    def test_us_stock_with_dot(self):
        self.assertEqual(normalize_stock_code("BRK.B"), "BRK.B")


@unittest.skipIf(not _BASE_IMPORTS_OK, f"base imports failed: {_BASE_IMPORT_ERROR}")
class TestCanonicalStockCode(unittest.TestCase):
    """Tests for canonical_stock_code()."""

    def test_lowercase_us(self):
        self.assertEqual(canonical_stock_code("aapl"), "AAPL")

    def test_korean_code(self):
        self.assertEqual(canonical_stock_code("005930"), "005930")


if __name__ == "__main__":
    unittest.main()

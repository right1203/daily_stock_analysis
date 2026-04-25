# -*- coding: utf-8 -*-
"""Tests for DatabaseManager.get_latest_data()."""

import os
import tempfile
import unittest
from datetime import date, timedelta

import pandas as pd

from src.config import Config
from src.storage import DatabaseManager, StockDaily


class GetLatestDataTestCase(unittest.TestCase):
    """Tests for get_latest_data behavior."""

    def setUp(self) -> None:
        """Initialize an isolated database for each test case."""
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_get_latest_data.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        """Clean up resources."""
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def _insert_stock_data(self, code: str, days_ago: int, close: float) -> None:
        """Insert stock data for a test case."""
        target_date = date.today() - timedelta(days=days_ago)
        df = pd.DataFrame([{
            'date': target_date,
            'open': close - 1,
            'high': close + 1,
            'low': close - 2,
            'close': close,
            'volume': 1000000,
            'amount': 10000000,
            'pct_chg': 1.5,
        }])
        self.db.save_daily_data(df, code, data_source="TestData")

    def test_get_latest_data_returns_empty_when_no_data(self) -> None:
        """Return an empty list when no data exists."""
        result = self.db.get_latest_data("999999", days=2)
        self.assertEqual(result, [])

    def test_get_latest_data_returns_correct_count(self) -> None:
        """Return the requested number of rows."""
        # Insert five days of data.
        for i in range(5):
            self._insert_stock_data("005930", days_ago=i, close=100.0 + i)

        # Request two days of data.
        result = self.db.get_latest_data("005930", days=2)
        self.assertEqual(len(result), 2)

        # Request five days of data.
        result = self.db.get_latest_data("005930", days=5)
        self.assertEqual(len(result), 5)

    def test_get_latest_data_ordered_by_date_desc(self) -> None:
        """Return data ordered by date descending."""
        # Insert three days of data.
        for i in range(3):
            self._insert_stock_data("005930", days_ago=i, close=100.0 + i)

        result = self.db.get_latest_data("005930", days=3)

        # Verify descending dates with newest first.
        self.assertEqual(len(result), 3)
        self.assertGreater(result[0].date, result[1].date)
        self.assertGreater(result[1].date, result[2].date)

    def test_get_latest_data_filters_by_code(self) -> None:
        """Filter rows by stock code."""
        # Insert data for different stocks.
        self._insert_stock_data("005930", days_ago=0, close=100.0)
        self._insert_stock_data("035720", days_ago=0, close=50.0)

        result = self.db.get_latest_data("005930", days=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, "005930")


if __name__ == "__main__":
    unittest.main()

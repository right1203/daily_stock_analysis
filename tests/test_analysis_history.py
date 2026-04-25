# -*- coding: utf-8 -*-
"""Tests for analysis history storage."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

# Keep this test runnable when optional LLM runtime deps are not installed.
try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from src.config import Config
from src.storage import DatabaseManager, AnalysisHistory
from src.analyzer import AnalysisResult
from src.services.history_service import HistoryService


class AnalysisHistoryTestCase(unittest.TestCase):
    """Tests for analysis history storage."""

    def setUp(self) -> None:
        """Initialize an isolated database for each test case."""
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_analysis_history.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        """Clean up resources."""
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def _build_result(self) -> AnalysisResult:
        """Build an analysis result fixture."""
        return AnalysisResult(
            code="005930",
            name="삼성전자",
            sentiment_score=78,
            trend_prediction="강세",
            operation_advice="보유",
            analysis_summary="펀더멘털은 안정적이고 단기 흐름은 변동성 구간입니다",
        )

    def test_save_analysis_history_with_snapshot(self) -> None:
        """Save history with a context snapshot."""
        result = self._build_result()
        result.dashboard = {
            "battle_plan": {
                "sniper_points": {
                    "ideal_buy": "ideal buy: 125.5",
                    "secondary_buy": "120",
                    "stop_loss": "stop loss: 110",
                    "take_profit": "target: 150.0",
                }
            }
        }
        context_snapshot = {"enhanced_context": {"code": "005930"}}

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_001",
            report_type="simple",
            news_content="뉴스 요약",
            context_snapshot=context_snapshot,
            save_snapshot=True
        )

        self.assertEqual(saved, 1)

        history = self.db.get_analysis_history(code="005930", days=7, limit=10)
        self.assertEqual(len(history), 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).first()
            if row is None:
                self.fail("Saved history record was not found")
            self.assertEqual(row.query_id, "query_001")
            self.assertIsNotNone(row.context_snapshot)
            self.assertEqual(row.ideal_buy, 125.5)
            self.assertEqual(row.secondary_buy, 120.0)
            self.assertEqual(row.stop_loss, 110.0)
            self.assertEqual(row.take_profit, 150.0)

    def test_save_analysis_history_without_snapshot(self) -> None:
        """Do not write context_snapshot when snapshot saving is disabled."""
        result = self._build_result()

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_002",
            report_type="simple",
            news_content="뉴스 요약",
            context_snapshot={"foo": "bar"},
            save_snapshot=False
        )

        self.assertEqual(saved, 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).first()
            if row is None:
                self.fail("Saved history record was not found")
            self.assertIsNone(row.context_snapshot)

    def test_save_analysis_history_persists_model_used(self) -> None:
        """model_used should be persisted in raw_result for history detail."""
        result = self._build_result()
        result.model_used = "gemini/gemini-2.0-flash"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_003",
            report_type="simple",
            news_content="뉴스 요약",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertEqual(saved, 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_003").first()
            if row is None:
                self.fail("Saved history record was not found")
            payload = json.loads(row.raw_result or "{}")
            self.assertEqual(payload.get("model_used"), "gemini/gemini-2.0-flash")

    def test_history_detail_hides_placeholder_model_used(self) -> None:
        """Placeholder model values should be normalized to None in detail response."""
        result = self._build_result()
        result.model_used = "unknown"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_004",
            report_type="simple",
            news_content="뉴스 요약",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertEqual(saved, 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_004").first()
            if row is None:
                self.fail("Saved history record was not found")
            record_id = row.id

        service = HistoryService(self.db)
        detail = service.get_history_detail_by_id(record_id)
        self.assertIsNotNone(detail)
        self.assertIsNone(detail.get("model_used"))

    def test_history_detail_accepts_dict_raw_result(self) -> None:
        """_record_to_detail_dict should handle dict raw_result without json.loads errors."""
        result = self._build_result()
        result.model_used = "gemini/gemini-2.0-flash"
        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_005",
            report_type="simple",
            news_content="뉴스 요약",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertEqual(saved, 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_005").first()
            if row is None:
                self.fail("Saved history record was not found")
            row.raw_result = {"model_used": "unknown", "extra": "v"}

            service = HistoryService(self.db)
            detail = service._record_to_detail_dict(row)

        self.assertIsNotNone(detail)
        self.assertIsInstance(detail.get("raw_result"), dict)
        self.assertIsNone(detail.get("model_used"))


if __name__ == "__main__":
    unittest.main()

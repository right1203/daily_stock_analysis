# -*- coding: utf-8 -*-
"""
===================================
Unit tests for KR/US stock news intelligence storage
===================================

Scope:
1. Verify saving and deduplication for news intelligence
2. Verify fallback deduplication keys when URL is missing
"""

import os
import tempfile
import unittest

from datetime import datetime

from src.config import Config
from src.storage import DatabaseManager, NewsIntel
from src.search_service import SearchResponse, SearchResult


class NewsIntelStorageTestCase(unittest.TestCase):
    """News intelligence storage tests"""

    def setUp(self) -> None:
        """Initialize an isolated database for each case"""
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_news_intel.db")
        os.environ["DATABASE_PATH"] = self._db_path

        # Reset config and database singletons to use the temporary database
        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        """Clean up resources"""
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def _build_response(self, results) -> SearchResponse:
        """Build a SearchResponse helper"""
        return SearchResponse(
            query="삼성전자 최신 뉴스",
            results=results,
            provider="Naver",
            success=True,
        )

    def test_save_news_intel_with_url_dedup(self) -> None:
        """Same URL should be deduplicated into one record"""
        result = SearchResult(
            title="삼성전자 신제품 출시",
            snippet="회사가 신제품을 공개했습니다...",
            url="https://news.example.com/a",
            source="example.com",
            published_date="2025-01-02"
        )
        response = self._build_response([result])

        query_context = {
            "query_id": "task_001",
            "query_source": "bot",
            "requester_platform": "telegram",
            "requester_user_id": "u_123",
            "requester_user_name": "테스트 사용자",
            "requester_chat_id": "c_456",
            "requester_message_id": "m_789",
            "requester_query": "/analyze 005930",
        }

        saved_first = self.db.save_news_intel(
            code="005930",
            name="삼성전자",
            dimension="latest_news",
            query=response.query,
            response=response,
            query_context=query_context
        )
        saved_second = self.db.save_news_intel(
            code="005930",
            name="삼성전자",
            dimension="latest_news",
            query=response.query,
            response=response,
            query_context=query_context
        )

        self.assertEqual(saved_first, 1)
        self.assertEqual(saved_second, 0)

        with self.db.get_session() as session:
            total = session.query(NewsIntel).count()
            row = session.query(NewsIntel).first()
        self.assertEqual(total, 1)
        if row is None:
            self.fail("Saved news record was not found")
        self.assertEqual(row.query_id, "task_001")
        self.assertEqual(row.requester_user_name, "테스트 사용자")

    def test_save_news_intel_without_url_fallback_key(self) -> None:
        """Missing URL should use fallback key deduplication"""
        result = SearchResult(
            title="삼성전자 실적 전망",
            snippet="실적이 크게 개선되었습니다...",
            url="",
            source="example.com",
            published_date="2025-01-03"
        )
        response = self._build_response([result])

        saved_first = self.db.save_news_intel(
            code="005930",
            name="삼성전자",
            dimension="earnings",
            query=response.query,
            response=response
        )
        saved_second = self.db.save_news_intel(
            code="005930",
            name="삼성전자",
            dimension="earnings",
            query=response.query,
            response=response
        )

        self.assertEqual(saved_first, 1)
        self.assertEqual(saved_second, 0)

        with self.db.get_session() as session:
            row = session.query(NewsIntel).first()
            if row is None:
                self.fail("Saved news record was not found")
            self.assertTrue(row.url.startswith("no-url:"))

    def test_get_recent_news(self) -> None:
        """Recent news can be queried by time range"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = SearchResult(
            title="삼성전자 주가 변동",
            snippet="장중 변동성이 컸습니다...",
            url="https://news.example.com/b",
            source="example.com",
            published_date=now
        )
        response = self._build_response([result])

        self.db.save_news_intel(
            code="005930",
            name="삼성전자",
            dimension="market_analysis",
            query=response.query,
            response=response
        )

        recent_news = self.db.get_recent_news(code="005930", days=7, limit=10)
        self.assertEqual(len(recent_news), 1)
        self.assertEqual(recent_news[0].title, "삼성전자 주가 변동")


if __name__ == "__main__":
    unittest.main()

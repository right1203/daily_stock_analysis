# -*- coding: utf-8 -*-
"""Analysis history repository with CRUD helpers."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from src.storage import DatabaseManager, AnalysisHistory

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """Database access layer for AnalysisHistory rows."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the repository."""
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_by_query_id(self, query_id: str) -> Optional[AnalysisHistory]:
        """Return one analysis history record by query ID."""
        try:
            records = self.db.get_analysis_history(query_id=query_id, limit=1)
            return records[0] if records else None
        except Exception as e:
            logger.error("Failed to query analysis record: %s", e)
            return None
    
    def get_list(
        self,
        code: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """Return analysis history records with optional stock filter."""
        try:
            return self.db.get_analysis_history(
                code=code,
                days=days,
                limit=limit
            )
        except Exception as e:
            logger.error("Failed to get analysis list: %s", e)
            return []
    
    def save(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> int:
        """Save an analysis result and return saved count."""
        try:
            return self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type=report_type,
                news_content=news_content,
                context_snapshot=context_snapshot
            )
        except Exception as e:
            logger.error("Failed to save analysis result: %s", e)
            return 0
    
    def count_by_code(self, code: str, days: int = 30) -> int:
        """Count analysis records for a stock within the given day range."""
        try:
            records = self.db.get_analysis_history(code=code, days=days, limit=1000)
            return len(records)
        except Exception as e:
            logger.error("Failed to count analysis records: %s", e)
            return 0

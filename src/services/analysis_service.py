# -*- coding: utf-8 -*-
"""
===================================
Analysis service layer
===================================

Responsibilities:
1. Encapsulate stock analysis logic.
2. Call analyzer and pipeline execution.
3. Save analysis results to the database.
"""

import logging
import uuid
from typing import Optional, Dict, Any

from src.repositories.analysis_repo import AnalysisRepository

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Analysis service.

    Encapsulates stock analysis business logic.
    """

    def __init__(self):
        """Initialize analysis service."""
        self.repo = AnalysisRepository()

    def analyze_stock(
        self,
        stock_code: str,
        report_type: str = "detailed",
        force_refresh: bool = False,
        query_id: Optional[str] = None,
        send_notification: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Run stock analysis.

        Args:
            stock_code: Stock code.
            report_type: Report type, such as simple or detailed.
            force_refresh: Whether to force refresh.
            query_id: Optional query ID.
            send_notification: Whether to send notification; API-triggered
                analysis sends notifications by default.

        Returns:
            Analysis result dict containing stock_code, stock_name, and report.
        """
        try:
            # Import analysis modules lazily.
            from src.config import get_config
            from src.core.pipeline import StockAnalysisPipeline
            from src.enums import ReportType

            # Generate query_id when absent.
            if query_id is None:
                query_id = uuid.uuid4().hex

            # Load config.
            config = get_config()

            # Create analysis pipeline.
            pipeline = StockAnalysisPipeline(
                config=config,
                query_id=query_id,
                query_source="api"
            )

            # Resolve report type.
            rt = ReportType.FULL if report_type == "detailed" else ReportType.SIMPLE

            # Run analysis.
            result = pipeline.process_single_stock(
                code=stock_code,
                skip_analysis=False,
                single_stock_notify=send_notification,
                report_type=rt
            )

            if result is None:
                logger.warning(f"Stock {stock_code} analysis returned an empty result")
                return None

            # Build response.
            return self._build_analysis_response(result, query_id)

        except Exception as e:
            logger.error(f"Stock {stock_code} analysis failed: {e}", exc_info=True)
            return None

    def _build_analysis_response(
        self,
        result: Any,
        query_id: str
    ) -> Dict[str, Any]:
        """
        Build analysis response.

        Args:
            result: AnalysisResult object.
            query_id: Query ID.

        Returns:
            Formatted response dict.
        """
        # Get strategy price points.
        sniper_points = {}
        if hasattr(result, 'get_sniper_points'):
            sniper_points = result.get_sniper_points() or {}

        # Calculate sentiment label.
        sentiment_label = self._get_sentiment_label(result.sentiment_score)

        # Build report structure.
        report = {
            "meta": {
                "query_id": query_id,
                "stock_code": result.code,
                "stock_name": result.name,
                "report_type": "detailed",
                "current_price": result.current_price,
                "change_pct": result.change_pct,
                "model_used": getattr(result, "model_used", None),
            },
            "summary": {
                "analysis_summary": result.analysis_summary,
                "operation_advice": result.operation_advice,
                "trend_prediction": result.trend_prediction,
                "sentiment_score": result.sentiment_score,
                "sentiment_label": sentiment_label,
            },
            "strategy": {
                "ideal_buy": sniper_points.get("ideal_buy"),
                "secondary_buy": sniper_points.get("secondary_buy"),
                "stop_loss": sniper_points.get("stop_loss"),
                "take_profit": sniper_points.get("take_profit"),
            },
            "details": {
                "news_summary": result.news_summary,
                "technical_analysis": result.technical_analysis,
                "fundamental_analysis": result.fundamental_analysis,
                "risk_warning": result.risk_warning,
            }
        }
        
        return {
            "stock_code": result.code,
            "stock_name": result.name,
            "report": report,
        }

    def _get_sentiment_label(self, score: int) -> str:
        """
        Return sentiment label for a score.

        Args:
            score: Sentiment score from 0 to 100.

        Returns:
            Korean sentiment label.
        """
        if score >= 80:
            return "매우 긍정"
        elif score >= 60:
            return "긍정"
        elif score >= 40:
            return "중립"
        elif score >= 20:
            return "부정"
        else:
            return "매우 부정"

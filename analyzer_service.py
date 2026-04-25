# -*- coding: utf-8 -*-
"""
===================================
Stock Analysis System - Service Layer
===================================

Responsibilities:
1. Wrap core analysis logic for multiple callers (CLI, WebUI, Bot)
2. Provide a clear API independent of command-line arguments
3. Support dependency injection for testing and extension
4. Centralize analysis flow and configuration handling
"""

import uuid
from typing import List, Optional

from src.analyzer import AnalysisResult
from src.config import get_config, Config
from src.notification import NotificationService
from src.enums import ReportType
from src.core.pipeline import StockAnalysisPipeline
from src.core.market_review import run_market_review



def analyze_stock(
    stock_code: str,
    config: Config = None,
    full_report: bool = False,
    notifier: Optional[NotificationService] = None
) -> Optional[AnalysisResult]:
    """
    Analyze a single stock.
    
    Args:
        stock_code: Stock code.
        config: Config object (optional; singleton by default).
        full_report: Whether to generate a full report.
        notifier: Notification service (optional).
        
    Returns:
        AnalysisResult object.
    """
    if config is None:
        config = get_config()
    
    # Build analysis pipeline
    pipeline = StockAnalysisPipeline(
        config=config,
        query_id=uuid.uuid4().hex,
        query_source="cli"
    )
    
    # Use provided notifier when available
    if notifier:
        pipeline.notifier = notifier
    
    # Pick report type from full_report flag
    report_type = ReportType.FULL if full_report else ReportType.SIMPLE
    
    # Run single-stock analysis
    result = pipeline.process_single_stock(
        code=stock_code,
        skip_analysis=False,
        single_stock_notify=notifier is not None,
        report_type=report_type
    )
    
    return result

def analyze_stocks(
    stock_codes: List[str],
    config: Config = None,
    full_report: bool = False,
    notifier: Optional[NotificationService] = None
) -> List[AnalysisResult]:
    """
    Analyze multiple stocks.
    
    Args:
        stock_codes: List of stock codes.
        config: Config object (optional; singleton by default).
        full_report: Whether to generate a full report.
        notifier: Notification service (optional).
        
    Returns:
        List of analysis results.
    """
    if config is None:
        config = get_config()
    
    results = []
    for stock_code in stock_codes:
        result = analyze_stock(stock_code, config, full_report, notifier)
        if result:
            results.append(result)
    
    return results

def perform_market_review(
    config: Config = None,
    notifier: Optional[NotificationService] = None
) -> Optional[str]:
    """
    Run market review.
    
    Args:
        config: Config object (optional; singleton by default).
        notifier: Notification service (optional).
        
    Returns:
        Market review report content.
    """
    if config is None:
        config = get_config()
    
    # Build pipeline to reuse analyzer and search service
    pipeline = StockAnalysisPipeline(
        config=config,
        query_id=uuid.uuid4().hex,
        query_source="cli"
    )
    
    # Reuse provided notifier when available
    review_notifier = notifier or pipeline.notifier
    
    # Run market review flow
    return run_market_review(
        notifier=review_notifier,
        analyzer=pipeline.analyzer,
        search_service=pipeline.search_service
    )


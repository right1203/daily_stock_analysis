# -*- coding: utf-8 -*-
"""
===================================
History Endpoints
===================================

Responsibilities:
1. Provide the GET /api/v1/history history-list endpoint
2. Provide the GET /api/v1/history/{query_id} history-detail endpoint
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from api.deps import get_database_manager
from api.v1.schemas.history import (
    HistoryListResponse,
    HistoryItem,
    NewsIntelItem,
    NewsIntelResponse,
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
)
from api.v1.schemas.common import ErrorResponse
from src.storage import DatabaseManager
from src.services.history_service import HistoryService
from src.utils.data_processing import normalize_model_used

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HistoryListResponse,
    responses={
        200: {"description": "히스토리 기록 목록"},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="히스토리 분석 목록 조회",
    description=(
        "히스토리 분석 기록 요약을 페이지 단위로 조회하며, "
        "종목 코드와 날짜 범위로 필터링할 수 있습니다."
    ),
)
def get_history_list(
    stock_code: Optional[str] = Query(None, description="종목 코드 필터"),
    start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> HistoryListResponse:
    """
    Get the historical analysis list.
    
    Returns paginated historical analysis summaries with optional stock-code and date-range filters.
    
    Args:
        stock_code: Stock-code filter.
        start_date: Start date.
        end_date: End date.
        page: Page number.
        limit: Items per page.
        db_manager: Database manager dependency.
        
    Returns:
        HistoryListResponse: Historical record list.
    """
    try:
        service = HistoryService(db_manager)
        
        # Use def instead of async def so FastAPI runs this in the thread pool.
        result = service.get_history_list(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit
        )
        
        # Convert service data to response models.
        items = [
            HistoryItem(
                id=item.get("id"),
                query_id=item.get("query_id", ""),
                stock_code=item.get("stock_code", ""),
                stock_name=item.get("stock_name"),
                report_type=item.get("report_type"),
                sentiment_score=item.get("sentiment_score"),
                operation_advice=item.get("operation_advice"),
                created_at=item.get("created_at")
            )
            for item in result.get("items", [])
        ]
        
        return HistoryListResponse(
            total=result.get("total", 0),
            page=page,
            limit=limit,
            items=items
        )
        
    except Exception as e:
        logger.error(f"히스토리 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"히스토리 목록 조회 실패: {str(e)}"
            }
        )


@router.get(
    "/{record_id}",
    response_model=AnalysisReport,
    responses={
        200: {"description": "보고서 상세"},
        404: {"description": "보고서를 찾을 수 없음", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="히스토리 보고서 상세 조회",
    description=(
        "분석 히스토리 기록 ID 또는 query_id로 전체 히스토리 분석 보고서를 조회합니다."
    ),
)
def get_history_detail(
    record_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> AnalysisReport:
    """
    Get historical report details.
    
    Retrieves the full historical analysis report by primary key ID or query_id.
    Integer primary-key lookup is attempted first, then string query_id lookup.
    
    Args:
        record_id: Analysis history primary key ID or query_id.
        db_manager: Database manager dependency.
        
    Returns:
        AnalysisReport: Full analysis report.
        
    Raises:
        HTTPException: 404 when the report does not exist.
    """
    try:
        service = HistoryService(db_manager)
        
        # Try integer ID first, fall back to query_id string lookup
        result = service.resolve_and_get_detail(record_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"id/query_id={record_id} 분석 기록을 찾을 수 없습니다."
                }
            )
        
        # Extract price information from context_snapshot.
        current_price = None
        change_pct = None
        context_snapshot = result.get("context_snapshot")
        if context_snapshot and isinstance(context_snapshot, dict):
            # Try enhanced_context.realtime first.
            enhanced_context = context_snapshot.get("enhanced_context") or {}
            realtime = enhanced_context.get("realtime") or {}
            current_price = realtime.get("price")
            change_pct = realtime.get("change_pct") or realtime.get("change_60d")
            
            # Fall back to realtime_quote_raw.
            if current_price is None:
                realtime_quote_raw = context_snapshot.get("realtime_quote_raw") or {}
                current_price = realtime_quote_raw.get("price")
                change_pct = change_pct or realtime_quote_raw.get("change_pct") or realtime_quote_raw.get("pct_chg")
        
        # Build response models.
        meta = ReportMeta(
            id=result.get("id"),
            query_id=result.get("query_id", ""),
            stock_code=result.get("stock_code", ""),
            stock_name=result.get("stock_name"),
            report_type=result.get("report_type"),
            created_at=result.get("created_at"),
            current_price=current_price,
            change_pct=change_pct,
            model_used=normalize_model_used(result.get("model_used"))
        )
        
        summary = ReportSummary(
            analysis_summary=result.get("analysis_summary"),
            operation_advice=result.get("operation_advice"),
            trend_prediction=result.get("trend_prediction"),
            sentiment_score=result.get("sentiment_score"),
            sentiment_label=result.get("sentiment_label")
        )
        
        strategy = ReportStrategy(
            ideal_buy=result.get("ideal_buy"),
            secondary_buy=result.get("secondary_buy"),
            stop_loss=result.get("stop_loss"),
            take_profit=result.get("take_profit")
        )
        
        details = ReportDetails(
            news_content=result.get("news_content"),
            raw_result=result.get("raw_result"),
            context_snapshot=result.get("context_snapshot")
        )
        
        return AnalysisReport(
            meta=meta,
            summary=summary,
            strategy=strategy,
            details=details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"히스토리 상세 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"히스토리 상세 조회 실패: {str(e)}"
            }
        )


@router.get(
    "/{record_id}/news",
    response_model=NewsIntelResponse,
    responses={
        200: {"description": "뉴스 인텔리전스 목록"},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="히스토리 보고서 관련 뉴스 조회",
    description=(
        "분석 히스토리 기록 ID로 관련 뉴스 인텔리전스 목록을 조회합니다. "
        "결과가 없어도 200을 반환합니다."
    ),
)
def get_history_news(
    record_id: str,
    limit: int = Query(20, ge=1, le=100, description="반환 항목 수 제한"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> NewsIntelResponse:
    """
    Get news related to a historical report.

    Retrieves related news intelligence by analysis history ID or query_id.
    The record_id to query_id resolution is handled internally.

    Args:
        record_id: Analysis history primary key ID or query_id.
        limit: Return item limit.
        db_manager: Database manager dependency.

    Returns:
        NewsIntelResponse: News intelligence list.
    """
    try:
        service = HistoryService(db_manager)
        items = service.resolve_and_get_news(record_id=record_id, limit=limit)

        response_items = [
            NewsIntelItem(
                title=item.get("title", ""),
                snippet=item.get("snippet"),
                url=item.get("url", "")
            )
            for item in items
        ]

        return NewsIntelResponse(
            total=len(response_items),
            items=response_items
        )

    except Exception as e:
        logger.error(f"뉴스 인텔리전스 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"뉴스 인텔리전스 조회 실패: {str(e)}"
            }
        )

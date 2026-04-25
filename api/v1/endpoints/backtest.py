# -*- coding: utf-8 -*-
"""Backtest endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestResultItem,
    BacktestResultsResponse,
    PerformanceMetrics,
)
from api.v1.schemas.common import ErrorResponse
from src.services.backtest_service import BacktestService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    response_model=BacktestRunResponse,
    responses={
        200: {"description": "백테스트 실행 완료"},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="백테스트 실행",
    description=(
        "히스토리 분석 기록을 백테스트 평가하고 "
        "backtest_results/backtest_summaries에 기록합니다."
    ),
)
def run_backtest(
    request: BacktestRunRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> BacktestRunResponse:
    try:
        service = BacktestService(db_manager)
        stats = service.run_backtest(
            code=request.code,
            force=request.force,
            eval_window_days=request.eval_window_days,
            min_age_days=request.min_age_days,
            limit=request.limit,
        )
        return BacktestRunResponse(**stats)
    except Exception as exc:
        logger.error(f"백테스트 실행 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"백테스트 실행 실패: {str(exc)}"},
        )


@router.get(
    "/results",
    response_model=BacktestResultsResponse,
    responses={
        200: {"description": "백테스트 결과 목록"},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="백테스트 결과 조회",
    description=(
        "백테스트 결과를 페이지 단위로 조회하며 종목 코드로 필터링할 수 있습니다."
    ),
)
def get_backtest_results(
    code: Optional[str] = Query(None, description="종목 코드 필터"),
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="평가 기간 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=200, description="페이지당 항목 수"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> BacktestResultsResponse:
    try:
        service = BacktestService(db_manager)
        data = service.get_recent_evaluations(code=code, eval_window_days=eval_window_days, limit=limit, page=page)
        items = [BacktestResultItem(**item) for item in data.get("items", [])]
        return BacktestResultsResponse(
            total=int(data.get("total", 0)),
            page=page,
            limit=limit,
            items=items,
        )
    except Exception as exc:
        logger.error(f"백테스트 결과 조회 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"백테스트 결과 조회 실패: {str(exc)}"},
        )


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    responses={
        200: {"description": "전체 백테스트 성과"},
        404: {"description": "백테스트 요약 없음", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="전체 백테스트 성과 조회",
)
def get_overall_performance(
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="평가 기간 필터"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> PerformanceMetrics:
    try:
        service = BacktestService(db_manager)
        summary = service.get_summary(scope="overall", code=None, eval_window_days=eval_window_days)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "전체 백테스트 요약을 찾을 수 없습니다."},
            )
        return PerformanceMetrics(**summary)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"전체 성과 조회 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"전체 성과 조회 실패: {str(exc)}"},
        )


@router.get(
    "/performance/{code}",
    response_model=PerformanceMetrics,
    responses={
        200: {"description": "개별 종목 백테스트 성과"},
        404: {"description": "백테스트 요약 없음", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="개별 종목 백테스트 성과 조회",
)
def get_stock_performance(
    code: str,
    eval_window_days: Optional[int] = Query(None, ge=1, le=120, description="평가 기간 필터"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> PerformanceMetrics:
    try:
        service = BacktestService(db_manager)
        summary = service.get_summary(scope="stock", code=code, eval_window_days=eval_window_days)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"{code} 백테스트 요약을 찾을 수 없습니다."},
            )
        return PerformanceMetrics(**summary)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"개별 종목 성과 조회 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"개별 종목 성과 조회 실패: {str(exc)}"},
        )

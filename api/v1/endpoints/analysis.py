# -*- coding: utf-8 -*-
"""
===================================
Stock analysis API endpoints
===================================

Responsibilities:
1. Provide POST /api/v1/analysis/analyze to trigger analysis.
2. Provide GET /api/v1/analysis/status/{task_id} to query task status.
3. Provide GET /api/v1/analysis/tasks to list tasks.
4. Provide GET /api/v1/analysis/tasks/stream for SSE updates.

Features:
- Async task queue: analysis runs without blocking requests.
- Duplicate prevention: returns 409 for a stock already being analyzed.
- SSE updates: task status changes are pushed to the frontend.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse

from api.deps import get_config_dep
from api.v1.schemas.analysis import (
    AnalyzeRequest,
    AnalysisResultResponse,
    TaskAccepted,
    TaskStatus,
    TaskInfo,
    TaskListResponse,
    DuplicateTaskErrorResponse,
)
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.history import (
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
)
from data_provider.base import canonical_stock_code
from src.config import Config
from src.services.task_queue import (
    get_task_queue,
    DuplicateTaskError,
    TaskStatus as TaskStatusEnum,
)
from src.utils.data_processing import normalize_model_used, parse_json_field

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# POST /analyze - trigger stock analysis.
# ============================================================

@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    responses={
        200: {"description": "분석 완료(동기 모드)", "model": AnalysisResultResponse},
        202: {"description": "분석 작업 접수됨(비동기 모드)", "model": TaskAccepted},
        400: {"description": "요청 파라미터 오류", "model": ErrorResponse},
        409: {
            "description": "해당 종목 분석이 진행 중이라 중복 제출이 거부됨",
            "model": DuplicateTaskErrorResponse,
        },
        500: {"description": "분석 실패", "model": ErrorResponse},
    },
    summary="종목 분석 실행",
    description=(
        "AI 종목 분석 작업을 시작합니다. 동기/비동기 모드를 지원하며 "
        "비동기 모드에서는 중복 제출을 막습니다."
    )
)
def trigger_analysis(
        request: AnalyzeRequest,
        config: Config = Depends(get_config_dep)
) -> Union[AnalysisResultResponse, JSONResponse]:
    """
    Trigger stock analysis.

    Starts an AI analysis task for one or more stock codes.

    Flow:
    1. Validate request parameters.
    2. Async mode: check duplicates, submit to task queue, return 202.
    3. Sync mode: run analysis directly and return 200.

    Args:
        request: Analysis request parameters.
        config: Config dependency.

    Returns:
        AnalysisResultResponse in sync mode or TaskAccepted in async mode.

    Raises:
        HTTPException: 400 for request errors, 409 for duplicate active tasks,
        or 500 for analysis failures.
    """
    # Validate request parameters.
    stock_codes = []
    if request.stock_code:
        stock_codes.append(request.stock_code)
    if request.stock_codes:
        stock_codes.extend(request.stock_codes)

    if not stock_codes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": "stock_code 또는 stock_codes 파라미터가 필요합니다."
            }
        )

    # Normalize and deduplicate so ['aapl', 'AAPL'] is treated as one stock.
    stock_codes = [canonical_stock_code(c) for c in stock_codes]
    stock_codes = list(dict.fromkeys(stock_codes))
    stock_code = stock_codes[0]  # Currently only the first code is processed.

    # Async mode: use the task queue.
    if request.async_mode:
        return _handle_async_analysis(stock_code, request)

    # Sync mode: run analysis directly.
    return _handle_sync_analysis(stock_code, request)


def _handle_async_analysis(
    stock_code: str,
    request: AnalyzeRequest
) -> JSONResponse:
    """
    Handle an asynchronous analysis request.

    Submits a task to the queue and returns 202 immediately. Returns 409 when
    the stock is already being analyzed.
    """
    task_queue = get_task_queue()
    
    try:
        # Submit task; DuplicateTaskError is raised for duplicate active tasks.
        task_info = task_queue.submit_task(
            stock_code=stock_code,
            stock_name=None,  # Name is resolved during analysis.
            report_type=request.report_type,
            force_refresh=request.force_refresh,
        )

        # Return 202 Accepted.
        task_accepted = TaskAccepted(
            task_id=task_info.task_id,
            status="pending",
            message=f"분석 작업이 대기열에 추가되었습니다: {stock_code}"
        )
        return JSONResponse(
            status_code=202,
            content=task_accepted.model_dump()
        )
        
    except DuplicateTaskError as e:
        # The stock is already being analyzed; return 409 Conflict.
        error_response = DuplicateTaskErrorResponse(
            error="duplicate_task",
            message=str(e),
            stock_code=e.stock_code,
            existing_task_id=e.existing_task_id,
        )
        return JSONResponse(
            status_code=409,
            content=error_response.model_dump()
        )


def _handle_sync_analysis(
    stock_code: str,
    request: AnalyzeRequest
) -> AnalysisResultResponse:
    """
    Handle a synchronous analysis request.

    Runs analysis directly and returns the result after completion.
    """
    import uuid
    from src.services.analysis_service import AnalysisService
    
    query_id = uuid.uuid4().hex
    
    try:
        service = AnalysisService()
        result = service.analyze_stock(
            stock_code=stock_code,
            report_type=request.report_type,
            force_refresh=request.force_refresh,
            query_id=query_id
        )

        if result is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "analysis_failed",
                    "message": f"{stock_code} 종목 분석에 실패했습니다."
                }
            )

        # Build report structure.
        report_data = result.get("report", {})
        report = _build_analysis_report(
            report_data, query_id, stock_code, result.get("stock_name")
        )

        return AnalysisResultResponse(
            query_id=query_id,
            stock_code=result.get("stock_code", stock_code),
            stock_name=result.get("stock_name"),
            report=report.model_dump() if report else None,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"분석 처리 중 오류가 발생했습니다: {str(e)}"
            }
        )


# ============================================================
# GET /tasks - list tasks.
# ============================================================

@router.get(
    "/tasks",
    response_model=TaskListResponse,
    responses={
        200: {"description": "작업 목록"},
    },
    summary="분석 작업 목록 조회",
    description="현재 분석 작업을 조회합니다. 상태로 필터링할 수 있습니다."
)
def get_task_list(
    status: Optional[str] = Query(
        None,
        description="필터 상태: pending, processing, completed, failed. 여러 값은 쉼표로 구분합니다."
    ),
    limit: int = Query(20, description="반환 개수 제한", ge=1, le=100),
) -> TaskListResponse:
    """
    Return analysis task list.

    Args:
        status: Optional status filter.
        limit: Result count limit.

    Returns:
        Task list response.
    """
    task_queue = get_task_queue()
    
    # Fetch all tasks.
    all_tasks = task_queue.list_all_tasks(limit=limit)
    
    # Filter by status.
    if status:
        status_list = [s.strip().lower() for s in status.split(",")]
        all_tasks = [t for t in all_tasks if t.status.value in status_list]
    
    # Statistics.
    stats = task_queue.get_task_stats()
    
    # Convert to schema.
    task_infos = [
        TaskInfo(
            task_id=t.task_id,
            stock_code=t.stock_code,
            stock_name=t.stock_name,
            status=t.status.value,
            progress=t.progress,
            message=t.message,
            report_type=t.report_type,
            created_at=t.created_at.isoformat(),
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            error=t.error,
        )
        for t in all_tasks
    ]
    
    return TaskListResponse(
        total=stats["total"],
        pending=stats["pending"],
        processing=stats["processing"],
        tasks=task_infos,
    )


# ============================================================
# GET /tasks/stream - SSE updates.
# ============================================================

@router.get(
    "/tasks/stream",
    responses={
        200: {"description": "SSE 이벤트 스트림", "content": {"text/event-stream": {}}},
    },
    summary="작업 상태 SSE 스트림",
    description="Server-Sent Events로 작업 상태 변경을 실시간 전송합니다."
)
async def task_stream():
    """
    Stream task status events over SSE.

    Event types:
    - connected: connected successfully
    - task_created: new task created
    - task_started: task started
    - task_completed: task completed
    - task_failed: task failed
    - heartbeat: heartbeat every 30 seconds

    Returns:
        SSE event stream response.
    """
    async def event_generator():
        task_queue = get_task_queue()
        event_queue: asyncio.Queue = asyncio.Queue()
        
        # Send connection event.
        yield _format_sse_event("connected", {"message": "Connected to task stream"})

        # Send currently active tasks.
        pending_tasks = task_queue.list_pending_tasks()
        for task in pending_tasks:
            yield _format_sse_event("task_created", task.to_dict())

        # Subscribe to task events.
        task_queue.subscribe(event_queue)

        try:
            while True:
                try:
                    # Wait for events and send heartbeat on timeout.
                    event = await asyncio.wait_for(event_queue.get(), timeout=30)
                    yield _format_sse_event(event["type"], event["data"])
                except asyncio.TimeoutError:
                    # Heartbeat.
                    yield _format_sse_event("heartbeat", {
                        "timestamp": datetime.now().isoformat()
                    })
        except asyncio.CancelledError:
            # Client disconnected.
            pass
        finally:
            task_queue.unsubscribe(event_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering.
        }
    )


def _format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format an SSE event.

    Args:
        event_type: Event type.
        data: Event payload.

    Returns:
        SSE-formatted string.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============================================================
# GET /status/{task_id} - get one task status.
# ============================================================

@router.get(
    "/status/{task_id}",
    response_model=TaskStatus,
    responses={
        200: {"description": "작업 상태"},
        404: {"description": "작업을 찾을 수 없음", "model": ErrorResponse},
    },
    summary="분석 작업 상태 조회",
    description="task_id로 단일 작업 상태를 조회합니다."
)
def get_analysis_status(task_id: str) -> TaskStatus:
    """
    Return analysis task status.

    The task queue is checked first. If no task exists, completed analysis
    history is queried from the database.

    Args:
        task_id: Task ID.

    Returns:
        Task status information.

    Raises:
        HTTPException: 404 when the task does not exist.
    """
    # 1. Check task queue first.
    task_queue = get_task_queue()
    task = task_queue.get_task(task_id)
    
    if task:
        return TaskStatus(
            task_id=task.task_id,
            status=task.status.value,
            progress=task.progress,
            result=None,  # Active tasks do not have a result yet.
            error=task.error,
        )

    # 2. Query completed records from the database.
    try:
        from src.storage import DatabaseManager
        db = DatabaseManager.get_instance()
        records = db.get_analysis_history(query_id=task_id, limit=1)

        if records:
            record = records[0]
            raw_result = parse_json_field(record.raw_result)
            model_used = normalize_model_used(
                (raw_result or {}).get("model_used") if isinstance(raw_result, dict) else None
            )
            # Build report from DB record so completed tasks return real data
            report_dict = AnalysisReport(
                meta=ReportMeta(
                    id=record.id,
                    query_id=task_id,
                    stock_code=record.code,
                    stock_name=record.name,
                    report_type=getattr(record, 'report_type', None),
                    created_at=record.created_at.isoformat() if record.created_at else None,
                    model_used=model_used,
                ),
                summary=ReportSummary(
                    sentiment_score=record.sentiment_score,
                    operation_advice=record.operation_advice,
                    trend_prediction=record.trend_prediction,
                    analysis_summary=record.analysis_summary,
                ),
                strategy=ReportStrategy(
                    ideal_buy=(
                        str(getattr(record, 'ideal_buy', None))
                        if getattr(record, 'ideal_buy', None) is not None
                        else None
                    ),
                    secondary_buy=(
                        str(getattr(record, 'secondary_buy', None))
                        if getattr(record, 'secondary_buy', None) is not None
                        else None
                    ),
                    stop_loss=(
                        str(getattr(record, 'stop_loss', None))
                        if getattr(record, 'stop_loss', None) is not None
                        else None
                    ),
                    take_profit=(
                        str(getattr(record, 'take_profit', None))
                        if getattr(record, 'take_profit', None) is not None
                        else None
                    ),
                ),
            ).model_dump()
            return TaskStatus(
                task_id=task_id,
                status="completed",
                progress=100,
                result=AnalysisResultResponse(
                    query_id=task_id,
                    stock_code=record.code,
                    stock_name=record.name,
                    report=report_dict,
                    created_at=record.created_at.isoformat() if record.created_at else datetime.now().isoformat()
                ),
                error=None
            )

    except Exception as e:
        logger.error(f"Failed to query task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"작업 상태 조회에 실패했습니다: {str(e)}"
            }
        )

    # 3. Task does not exist.
    raise HTTPException(
        status_code=404,
        detail={
            "error": "not_found",
            "message": f"작업 {task_id}을 찾을 수 없거나 만료되었습니다."
        }
    )


# ============================================================
# Helper functions.
# ============================================================

def _build_analysis_report(
        report_data: Dict[str, Any],
        query_id: str,
        stock_code: str,
        stock_name: Optional[str] = None
) -> AnalysisReport:
    """
    Build an analysis report that follows the API schema.

    Args:
        report_data: Raw report data.
        query_id: Query ID.
        stock_code: Stock code.
        stock_name: Stock name.

    Returns:
        Structured analysis report.
    """
    meta_data = report_data.get("meta", {})
    summary_data = report_data.get("summary", {})
    strategy_data = report_data.get("strategy", {})
    details_data = report_data.get("details", {})

    meta = ReportMeta(
        query_id=meta_data.get("query_id", query_id),
        stock_code=meta_data.get("stock_code", stock_code),
        stock_name=meta_data.get("stock_name", stock_name),
        report_type=meta_data.get("report_type", "detailed"),
        created_at=meta_data.get("created_at", datetime.now().isoformat()),
        current_price=meta_data.get("current_price"),
        change_pct=meta_data.get("change_pct"),
        model_used=normalize_model_used(meta_data.get("model_used")),
    )

    summary = ReportSummary(
        analysis_summary=summary_data.get("analysis_summary"),
        operation_advice=summary_data.get("operation_advice"),
        trend_prediction=summary_data.get("trend_prediction"),
        sentiment_score=summary_data.get("sentiment_score"),
        sentiment_label=summary_data.get("sentiment_label")
    )

    strategy = None
    if strategy_data:
        strategy = ReportStrategy(
            ideal_buy=strategy_data.get("ideal_buy"),
            secondary_buy=strategy_data.get("secondary_buy"),
            stop_loss=strategy_data.get("stop_loss"),
            take_profit=strategy_data.get("take_profit")
        )

    details = None
    if details_data:
        details = ReportDetails(
            news_content=details_data.get("news_summary") or details_data.get("news_content"),
            raw_result=details_data,
            context_snapshot=None
        )

    return AnalysisReport(
        meta=meta,
        summary=summary,
        strategy=strategy,
        details=details
    )

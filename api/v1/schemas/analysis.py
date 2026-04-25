# -*- coding: utf-8 -*-
"""
===================================
Analysis API schemas
===================================

Responsibilities:
1. Define analysis request and response models.
2. Define task status models.
3. Define asynchronous task queue models.
"""

from typing import Optional, List, Any
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    """Task status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    """Analysis request model."""
    
    stock_code: Optional[str] = Field(
        None, 
        description="단일 종목 코드",
        example="005930"
    )
    stock_codes: Optional[List[str]] = Field(
        None, 
        description="여러 종목 코드(stock_code와 둘 중 하나 사용)",
        example=["005930", "AAPL"]
    )
    report_type: str = Field(
        "detailed", 
        description="리포트 유형",
        pattern="^(simple|detailed)$"
    )
    force_refresh: bool = Field(
        True,
        description="캐시를 무시하고 강제로 새로고침할지 여부"
    )
    async_mode: bool = Field(
        False,
        description="비동기 모드 사용 여부"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "report_type": "detailed",
                "force_refresh": False,
                "async_mode": False
            }
        }


class AnalysisResultResponse(BaseModel):
    """Analysis result response model."""
    
    query_id: str = Field(..., description="분석 기록 고유 ID")
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    report: Optional[Any] = Field(None, description="분석 리포트")
    created_at: str = Field(..., description="생성 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "abc123def456",
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "report": {
                    "summary": {
                        "sentiment_score": 75,
                        "operation_advice": "보유"
                    }
                },
                "created_at": "2024-01-01T12:00:00"
            }
        }


class TaskAccepted(BaseModel):
    """Asynchronous task acceptance response."""
    
    task_id: str = Field(..., description="상태 조회에 사용하는 작업 ID")
    status: str = Field(
        ..., 
        description="작업 상태",
        pattern="^(pending|processing)$"
    )
    message: Optional[str] = Field(None, description="안내 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "pending",
                "message": "Analysis task accepted"
            }
        }


class TaskStatus(BaseModel):
    """Task status model."""
    
    task_id: str = Field(..., description="작업 ID")
    status: str = Field(
        ..., 
        description="작업 상태",
        pattern="^(pending|processing|completed|failed)$"
    )
    progress: Optional[int] = Field(
        None, 
        description="진행률 (0-100)",
        ge=0,
        le=100
    )
    result: Optional[AnalysisResultResponse] = Field(
        None, 
        description="분석 결과(completed 상태에서만 존재)"
    )
    error: Optional[str] = Field(
        None, 
        description="오류 메시지(failed 상태에서만 존재)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "completed",
                "progress": 100,
                "result": None,
                "error": None
            }
        }


class TaskInfo(BaseModel):
    """Task detail model used by task lists and SSE events."""
    
    task_id: str = Field(..., description="작업 ID")
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    status: TaskStatusEnum = Field(..., description="작업 상태")
    progress: int = Field(0, description="진행률 (0-100)", ge=0, le=100)
    message: Optional[str] = Field(None, description="상태 메시지")
    report_type: str = Field("detailed", description="리포트 유형")
    created_at: str = Field(..., description="생성 시간")
    started_at: Optional[str] = Field(None, description="시작 시간")
    completed_at: Optional[str] = Field(None, description="완료 시간")
    error: Optional[str] = Field(None, description="오류 메시지(failed 상태에서만 존재)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123def456",
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "status": "processing",
                "progress": 50,
                "message": "분석 중...",
                "report_type": "detailed",
                "created_at": "2026-02-05T10:30:00",
                "started_at": "2026-02-05T10:30:01",
                "completed_at": None,
                "error": None
            }
        }


class TaskListResponse(BaseModel):
    """Task list response model."""
    
    total: int = Field(..., description="전체 작업 수")
    pending: int = Field(..., description="대기 중인 작업 수")
    processing: int = Field(..., description="처리 중인 작업 수")
    tasks: List[TaskInfo] = Field(..., description="작업 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 3,
                "pending": 1,
                "processing": 2,
                "tasks": []
            }
        }


class DuplicateTaskErrorResponse(BaseModel):
    """Duplicate task error response model."""
    
    error: str = Field("duplicate_task", description="오류 유형")
    message: str = Field(..., description="오류 메시지")
    stock_code: str = Field(..., description="종목 코드")
    existing_task_id: str = Field(..., description="이미 존재하는 작업 ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "duplicate_task",
                "message": "종목 005930 분석 작업이 이미 진행 중입니다",
                "stock_code": "005930",
                "existing_task_id": "abc123def456"
            }
        }

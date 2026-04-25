# -*- coding: utf-8 -*-
"""
===================================
Common response models
===================================

Responsibilities:
1. Define common response models such as HealthResponse and ErrorResponse.
2. Provide consistent response payload shapes.
"""

from typing import Optional, Any

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    """API root response."""
    
    message: str = Field(..., description="API status message", example="Daily Stock Analysis API is running")
    version: Optional[str] = Field(None, description="API version", example="1.0.0")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Daily Stock Analysis API is running",
                "version": "1.0.0"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status", example="ok")
    timestamp: Optional[str] = Field(None, description="Timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2024-01-01T12:00:00"
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    
    error: str = Field(..., description="Error type", example="validation_error")
    message: str = Field(..., description="Error detail", example="요청 파라미터 오류")
    detail: Optional[Any] = Field(None, description="Additional error information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "not_found",
                "message": "리소스를 찾을 수 없습니다",
                "detail": None
            }
        }


class SuccessResponse(BaseModel):
    """Common success response."""
    
    success: bool = Field(True, description="Whether the request succeeded")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Any] = Field(None, description="Response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "작업이 완료되었습니다",
                "data": None
            }
        }

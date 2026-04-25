# -*- coding: utf-8 -*-
"""
===================================
Global exception handling middleware
===================================

Responsibilities:
1. Catch unhandled exceptions.
2. Return consistent error response payloads.
3. Record error logs.
"""

import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global exception handling middleware.

    Catches unhandled exceptions and returns a consistent error payload.
    """
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """
        Process a request and catch exceptions.

        Args:
            request: Request object.
            call_next: Next handler.

        Returns:
            Response object.
        """
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Record error log.
            logger.error(
                f"Unhandled exception: {e}\n"
                f"Request path: {request.url.path}\n"
                f"Request method: {request.method}\n"
                f"Traceback: {traceback.format_exc()}"
            )

            # Return a consistent error response.
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None
                }
            )


def add_error_handlers(app) -> None:
    """
    Add global exception handlers.

    Args:
        app: FastAPI application instance.
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        # Use ErrorResponse-compatible detail payloads as-is.
        if isinstance(exc.detail, dict) and "error" in exc.detail and "message" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        # Wrap plain detail values in the standard response shape.
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": str(exc.detail) if exc.detail else "HTTP Error",
                "detail": None
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation exceptions."""
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "요청 파라미터 검증에 실패했습니다.",
                "detail": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle generic exceptions."""
        logger.error(
            f"Unhandled exception: {exc}\n"
            f"Request path: {request.url.path}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "서버 내부 오류가 발생했습니다.",
                "detail": None
            }
        )

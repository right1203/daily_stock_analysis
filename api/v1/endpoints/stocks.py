# -*- coding: utf-8 -*-
"""Stock data API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.v1.schemas.stocks import (
    ExtractFromImageResponse,
    KLineData,
    StockHistoryResponse,
    StockQuote,
)
from api.v1.schemas.common import ErrorResponse
from src.services.image_stock_extractor import (
    ALLOWED_MIME,
    MAX_SIZE_BYTES,
    extract_stock_codes_from_image,
)
from src.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()

# Define before the /{stock_code} routes.
ALLOWED_MIME_STR = ", ".join(ALLOWED_MIME)


@router.post(
    "/extract-from-image",
    response_model=ExtractFromImageResponse,
    responses={
        200: {"description": "추출된 종목 코드"},
        400: {"description": "이미지가 올바르지 않습니다", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="이미지에서 종목 코드 추출",
    description="스크린샷이나 이미지를 업로드하면 Vision LLM으로 종목 코드를 추출합니다. JPEG, PNG, WebP, GIF를 지원하며 최대 5MB입니다.",
)
def extract_from_image(
    file: Optional[UploadFile] = File(None, description="이미지 파일(form field name: file)"),
    include_raw: bool = Query(False, description="원본 LLM 응답 포함 여부"),
) -> ExtractFromImageResponse:
    """Extract stock codes from an uploaded image with a Vision LLM."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "파일이 없습니다. form field file로 이미지를 업로드하세요"},
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_type",
                "message": f"지원하지 않는 유형입니다: {content_type}. 허용: {ALLOWED_MIME_STR}",
            },
        )

    try:
        # Read up to the size limit, then reject if more bytes remain.
        data = file.file.read(MAX_SIZE_BYTES)
        if file.file.read(1):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "file_too_large",
                    "message": f"이미지가 {MAX_SIZE_BYTES // (1024 * 1024)}MB 제한을 초과했습니다",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "read_failed", "message": "업로드 파일을 읽지 못했습니다"},
        )

    try:
        codes, raw_text = extract_stock_codes_from_image(data, content_type)
        return ExtractFromImageResponse(
            codes=codes,
            raw_text=raw_text if include_raw else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "extract_failed", "message": str(e)})
    except Exception as e:
        logger.error(f"Image extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "이미지 추출에 실패했습니다"},
        )


@router.get(
    "/{stock_code}/quote",
    response_model=StockQuote,
    responses={
        200: {"description": "시세 데이터"},
        404: {"description": "종목을 찾을 수 없습니다", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="종목 실시간 시세 조회",
    description="지정한 종목의 최신 시세 데이터를 조회합니다"
)
def get_stock_quote(stock_code: str) -> StockQuote:
    """Get the latest quote for a stock."""
    try:
        service = StockService()
        
        # FastAPI runs regular def endpoints in a thread pool.
        result = service.get_realtime_quote(stock_code)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"{stock_code} 시세 데이터를 찾을 수 없습니다"
                }
            )
        
        return StockQuote(
            stock_code=result.get("stock_code", stock_code),
            stock_name=result.get("stock_name"),
            current_price=result.get("current_price", 0.0),
            change=result.get("change"),
            change_percent=result.get("change_percent"),
            open=result.get("open"),
            high=result.get("high"),
            low=result.get("low"),
            prev_close=result.get("prev_close"),
            volume=result.get("volume"),
            amount=result.get("amount"),
            update_time=result.get("update_time")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get realtime quote: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"실시간 시세 조회에 실패했습니다: {str(e)}"
            }
        )


@router.get(
    "/{stock_code}/history",
    response_model=StockHistoryResponse,
    responses={
        200: {"description": "과거 시세 데이터"},
        422: {"description": "지원하지 않는 기간 파라미터", "model": ErrorResponse},
        500: {"description": "서버 오류", "model": ErrorResponse},
    },
    summary="종목 과거 시세 조회",
    description="지정한 종목의 과거 OHLCV 데이터를 조회합니다"
)
def get_stock_history(
    stock_code: str,
    period: str = Query("daily", description="가격 주기", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="조회 일수")
) -> StockHistoryResponse:
    """Get historical OHLCV data for a stock."""
    try:
        service = StockService()
        
        # FastAPI runs regular def endpoints in a thread pool.
        result = service.get_history_data(
            stock_code=stock_code,
            period=period,
            days=days
        )
        
        # Convert service data into the response model.
        data = [
            KLineData(
                date=item.get("date"),
                open=item.get("open"),
                high=item.get("high"),
                low=item.get("low"),
                close=item.get("close"),
                volume=item.get("volume"),
                amount=item.get("amount"),
                change_percent=item.get("change_percent")
            )
            for item in result.get("data", [])
        ]
        
        return StockHistoryResponse(
            stock_code=stock_code,
            stock_name=result.get("stock_name"),
            period=period,
            data=data
        )
    
    except ValueError as e:
        # Unsupported period errors, such as weekly/monthly.
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_period",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to get historical prices: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"과거 시세 조회에 실패했습니다: {str(e)}"
            }
        )

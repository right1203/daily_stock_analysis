# -*- coding: utf-8 -*-
"""
===================================
Stock data API schemas
===================================

Responsibilities:
1. Define real-time quote models.
2. Define historical OHLCV models.
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """Real-time stock quote."""
    
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    current_price: float = Field(..., description="현재가")
    change: Optional[float] = Field(None, description="등락 금액")
    change_percent: Optional[float] = Field(None, description="등락률 (%)")
    open: Optional[float] = Field(None, description="시가")
    high: Optional[float] = Field(None, description="고가")
    low: Optional[float] = Field(None, description="저가")
    prev_close: Optional[float] = Field(None, description="전일 종가")
    volume: Optional[float] = Field(None, description="거래량")
    amount: Optional[float] = Field(None, description="거래대금")
    update_time: Optional[str] = Field(None, description="업데이트 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "current_price": 78000.00,
                "change": 500.00,
                "change_percent": 0.84,
                "open": 77500.00,
                "high": 78500.00,
                "low": 77200.00,
                "prev_close": 77500.00,
                "volume": 10000000,
                "amount": 18000000000,
                "update_time": "2024-01-01T15:00:00"
            }
        }


class KLineData(BaseModel):
    """Historical OHLCV data point."""
    
    date: str = Field(..., description="날짜")
    open: float = Field(..., description="시가")
    high: float = Field(..., description="고가")
    low: float = Field(..., description="저가")
    close: float = Field(..., description="종가")
    volume: Optional[float] = Field(None, description="거래량")
    amount: Optional[float] = Field(None, description="거래대금")
    change_percent: Optional[float] = Field(None, description="등락률 (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-01",
                "open": 1785.00,
                "high": 1810.00,
                "low": 1780.00,
                "close": 1800.00,
                "volume": 10000000,
                "amount": 18000000000,
                "change_percent": 0.84
            }
        }


class ExtractFromImageResponse(BaseModel):
    """Stock code extraction response for uploaded images."""

    codes: List[str] = Field(..., description="추출된 종목 코드(중복 제거)")
    raw_text: Optional[str] = Field(None, description="원본 LLM 응답(디버그용)")


class StockHistoryResponse(BaseModel):
    """Historical stock quote response."""
    
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    period: str = Field(..., description="가격 주기")
    data: List[KLineData] = Field(default_factory=list, description="가격 데이터 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "AAPL",
                "stock_name": "Apple Inc.",
                "period": "daily",
                "data": []
            }
        }

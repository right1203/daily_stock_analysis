# -*- coding: utf-8 -*-
"""Schemas for analysis history and report detail responses."""

from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict, Field


class HistoryItem(BaseModel):
    """History summary item used in list views."""

    id: Optional[int] = Field(None, description="분석 이력 기본 키 ID")
    query_id: str = Field(..., description="분석 기록의 query_id")
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    report_type: Optional[str] = Field(None, description="리포트 유형")
    sentiment_score: Optional[int] = Field(
        None, 
        description="심리 점수 (0-100)",
        ge=0,
        le=100
    )
    operation_advice: Optional[str] = Field(None, description="투자 판단")
    created_at: Optional[str] = Field(None, description="생성 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1234,
                "query_id": "abc123",
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "report_type": "detailed",
                "sentiment_score": 75,
                "operation_advice": "보유",
                "created_at": "2024-01-01T12:00:00"
            }
        }


class HistoryListResponse(BaseModel):
    """History list response."""
    
    total: int = Field(..., description="전체 기록 수")
    page: int = Field(..., description="현재 페이지")
    limit: int = Field(..., description="페이지당 개수")
    items: List[HistoryItem] = Field(default_factory=list, description="기록 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "limit": 20,
                "items": []
            }
        }


class NewsIntelItem(BaseModel):
    """News intelligence item."""

    title: str = Field(..., description="뉴스 제목")
    snippet: str = Field("", description="뉴스 요약")
    url: str = Field(..., description="뉴스 링크")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "삼성전자, 분기 실적 발표",
                "snippet": "삼성전자가 분기 실적과 향후 전망을 공개했습니다...",
                "url": "https://example.com/news/123"
            }
        }


class NewsIntelResponse(BaseModel):
    """News intelligence response."""

    total: int = Field(..., description="뉴스 수")
    items: List[NewsIntelItem] = Field(default_factory=list, description="뉴스 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "items": []
            }
        }


class ReportMeta(BaseModel):
    """Report metadata."""

    model_config = ConfigDict(protected_namespaces=("model_validate", "model_dump"))

    id: Optional[int] = Field(None, description="분석 이력 기본 키 ID")
    query_id: str = Field(..., description="분석 기록의 query_id")
    stock_code: str = Field(..., description="종목 코드")
    stock_name: Optional[str] = Field(None, description="종목명")
    report_type: Optional[str] = Field(None, description="리포트 유형")
    created_at: Optional[str] = Field(None, description="생성 시간")
    current_price: Optional[float] = Field(None, description="분석 시점 가격")
    change_pct: Optional[float] = Field(None, description="분석 시점 등락률(%)")
    model_used: Optional[str] = Field(None, description="분석에 사용한 LLM 모델")


class ReportSummary(BaseModel):
    """Report summary section."""
    
    analysis_summary: Optional[str] = Field(None, description="핵심 결론")
    operation_advice: Optional[str] = Field(None, description="투자 판단")
    trend_prediction: Optional[str] = Field(None, description="추세 전망")
    sentiment_score: Optional[int] = Field(
        None, 
        description="심리 점수 (0-100)",
        ge=0,
        le=100
    )
    sentiment_label: Optional[str] = Field(None, description="심리 라벨")


class ReportStrategy(BaseModel):
    """Strategy price section."""
    
    ideal_buy: Optional[str] = Field(None, description="우선 매수가")
    secondary_buy: Optional[str] = Field(None, description="보조 매수가")
    stop_loss: Optional[str] = Field(None, description="손절가")
    take_profit: Optional[str] = Field(None, description="목표가")


class ReportDetails(BaseModel):
    """Report detail section."""
    
    news_content: Optional[str] = Field(None, description="뉴스 요약")
    raw_result: Optional[Any] = Field(None, description="원본 분석 결과(JSON)")
    context_snapshot: Optional[Any] = Field(None, description="분석 시점 컨텍스트 스냅샷(JSON)")


class AnalysisReport(BaseModel):
    """Complete analysis report."""
    
    meta: ReportMeta = Field(..., description="메타 정보")
    summary: ReportSummary = Field(..., description="요약 영역")
    strategy: Optional[ReportStrategy] = Field(None, description="전략 가격 영역")
    details: Optional[ReportDetails] = Field(None, description="상세 영역")
    
    class Config:
        json_schema_extra = {
            "example": {
                "meta": {
                    "query_id": "abc123",
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "report_type": "detailed",
                    "created_at": "2024-01-01T12:00:00"
                },
                "summary": {
                    "analysis_summary": "기술적 흐름이 양호해 보유 관점이 유효합니다",
                    "operation_advice": "보유",
                    "trend_prediction": "강세",
                    "sentiment_score": 75,
                    "sentiment_label": "낙관"
                },
                "strategy": {
                    "ideal_buy": "1800.00",
                    "secondary_buy": "1750.00",
                    "stop_loss": "1700.00",
                    "take_profit": "2000.00"
                },
                "details": None
            }
        }

# -*- coding: utf-8 -*-
"""
===================================
데이터 소스 전략 레이어 - 패키지 초기화
===================================

전략 패턴으로 복수의 데이터 소스를 관리합니다:
1. 통합된 데이터 조회 인터페이스
2. 자동 장애 전환
3. 차단 방지 흐름 제어

Active data sources:
1. PykrxFetcher (Priority 0) - Korean market (KRX)
2. YfinanceFetcher (Priority 1) - US/global Yahoo Finance
"""

from .base import BaseFetcher, DataFetcherManager
from .pykrx_fetcher import PykrxFetcher
from .yfinance_fetcher import YfinanceFetcher
from .kr_index_mapping import KR_INDEX_MAPPING, get_kr_index_yf_symbol, is_kr_index_code, is_kr_stock_code
from .us_index_mapping import US_INDEX_MAPPING, get_us_index_yf_symbol, is_us_index_code, is_us_stock_code

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'PykrxFetcher',
    'YfinanceFetcher',
    'is_us_index_code',
    'is_us_stock_code',
    'is_kr_index_code',
    'is_kr_stock_code',
    'get_us_index_yf_symbol',
    'get_kr_index_yf_symbol',
    'US_INDEX_MAPPING',
    'KR_INDEX_MAPPING',
]

# -*- coding: utf-8 -*-
"""
===================================
데이터 소스 전략 레이어 - 패키지 초기화
===================================

전략 패턴으로 복수의 데이터 소스를 관리합니다:
1. 통합된 데이터 조회 인터페이스
2. 자동 장애 전환
3. 차단 방지 흐름 제어

데이터 소스 우선순위:
1. PykrxFetcher (Priority 0) - 한국 시장 (KRX)
2. YfinanceFetcher (Priority 1) - 글로벌 (미국 + 한국 폴백)

레거시 데이터 소스 (중국 시장, deprecated):
- EfinanceFetcher, AkshareFetcher, TushareFetcher, PytdxFetcher, BaostockFetcher
"""

from .base import BaseFetcher, DataFetcherManager
# Legacy China fetchers (kept for backwards compatibility, will be removed)
from .efinance_fetcher import EfinanceFetcher
from .akshare_fetcher import AkshareFetcher, is_hk_stock_code
from .tushare_fetcher import TushareFetcher
from .pytdx_fetcher import PytdxFetcher
from .baostock_fetcher import BaostockFetcher
# Active fetchers
from .yfinance_fetcher import YfinanceFetcher
from .pykrx_fetcher import PykrxFetcher
# Market detection utilities
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING
from .kr_index_mapping import is_kr_index_code, is_kr_stock_code, get_kr_index_yf_symbol, KR_INDEX_MAPPING

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'PykrxFetcher',
    'YfinanceFetcher',
    'EfinanceFetcher',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'is_us_index_code',
    'is_us_stock_code',
    'is_kr_index_code',
    'is_kr_stock_code',
    'is_hk_stock_code',
    'get_us_index_yf_symbol',
    'get_kr_index_yf_symbol',
    'US_INDEX_MAPPING',
    'KR_INDEX_MAPPING',
]

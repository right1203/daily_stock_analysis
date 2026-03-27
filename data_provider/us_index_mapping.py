# -*- coding: utf-8 -*-
"""
===================================
미국 주식 지수 및 종목 코드 유틸리티
===================================

제공:
1. 미국 지수 코드 매핑 (SPX -> ^GSPC)
2. 미국 종목 코드 식별 (AAPL, TSLA 등)

미국 지수는 Yahoo Finance에서 ^ 접두사를 사용합니다.
"""

import re

# 미국 종목 코드 정규식: 1-5개 대문자, 선택적 .X 접미사 (예: BRK.B)
_US_STOCK_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')


# 사용자 입력 -> (Yahoo Finance 심볼, 한국어 이름)
US_INDEX_MAPPING = {
    # S&P 500
    'SPX': ('^GSPC', 'S&P 500 지수'),
    '^GSPC': ('^GSPC', 'S&P 500 지수'),
    'GSPC': ('^GSPC', 'S&P 500 지수'),
    # 다우존스 산업평균지수
    'DJI': ('^DJI', '다우존스 산업지수'),
    '^DJI': ('^DJI', '다우존스 산업지수'),
    'DJIA': ('^DJI', '다우존스 산업지수'),
    # 나스닥 종합지수
    'IXIC': ('^IXIC', '나스닥 종합지수'),
    '^IXIC': ('^IXIC', '나스닥 종합지수'),
    'NASDAQ': ('^IXIC', '나스닥 종합지수'),
    # 나스닥 100
    'NDX': ('^NDX', '나스닥 100 지수'),
    '^NDX': ('^NDX', '나스닥 100 지수'),
    # VIX 변동성 지수
    'VIX': ('^VIX', 'VIX 공포지수'),
    '^VIX': ('^VIX', 'VIX 공포지수'),
    # 러셀 2000
    'RUT': ('^RUT', '러셀 2000 지수'),
    '^RUT': ('^RUT', '러셀 2000 지수'),
}


def is_us_index_code(code: str) -> bool:
    """코드가 미국 지수 심볼인지 판별합니다."""
    return (code or '').strip().upper() in US_INDEX_MAPPING


def is_us_stock_code(code: str) -> bool:
    """코드가 미국 주식 종목 코드인지 판별합니다 (지수 제외)."""
    normalized = (code or '').strip().upper()
    if normalized in US_INDEX_MAPPING:
        return False
    return bool(_US_STOCK_PATTERN.match(normalized))


def get_us_index_yf_symbol(code: str) -> tuple:
    """미국 지수의 Yahoo Finance 심볼과 한국어 이름을 반환합니다."""
    normalized = (code or '').strip().upper()
    return US_INDEX_MAPPING.get(normalized, (None, None))

# data_provider/kr_index_mapping.py
# -*- coding: utf-8 -*-
"""
===================================
한국 주식 지수 및 종목 코드 유틸리티
===================================

제공:
1. 한국 지수 코드 매핑 (KOSPI -> ^KS11)
2. 한국 종목 코드 식별 (005930, 035720 등)

한국 지수는 Yahoo Finance에서 ^ 접두사를 사용합니다.
"""

import re

# 한국 종목 코드 정규식: 6자리 숫자
_KR_STOCK_PATTERN = re.compile(r'^\d{6}$')

# 사용자 입력 -> (Yahoo Finance 심볼, 한국어 이름)
KR_INDEX_MAPPING = {
    # 코스피 종합지수
    'KOSPI': ('^KS11', '코스피 종합지수'),
    '^KS11': ('^KS11', '코스피 종합지수'),
    'KS11': ('^KS11', '코스피 종합지수'),
    # 코스닥 종합지수
    'KOSDAQ': ('^KQ11', '코스닥 종합지수'),
    '^KQ11': ('^KQ11', '코스닥 종합지수'),
    'KQ11': ('^KQ11', '코스닥 종합지수'),
    # 코스피 200
    'KS200': ('^KS200', '코스피 200'),
    'KOSPI200': ('^KS200', '코스피 200'),
    '^KS200': ('^KS200', '코스피 200'),
    # KRX 300
    'KRX300': ('^KRX300', 'KRX 300'),
}


def is_kr_index_code(code: str) -> bool:
    """코드가 한국 지수 심볼인지 판별합니다.

    Args:
        code: 주식/지수 코드, 예: 'KOSPI', 'KOSDAQ'

    Returns:
        True는 알려진 한국 지수 심볼, 아니면 False

    Examples:
        >>> is_kr_index_code('KOSPI')
        True
        >>> is_kr_index_code('005930')
        False
    """
    return (code or '').strip().upper() in KR_INDEX_MAPPING


def is_kr_stock_code(code: str) -> bool:
    """코드가 한국 주식 종목 코드인지 판별합니다 (지수 제외).

    한국 주식 종목 코드는 6자리 숫자입니다.
    한국 지수 코드(KOSPI, KOSDAQ 등)는 명확히 제외됩니다.

    Args:
        code: 종목 코드, 예: '005930', '035720'

    Returns:
        True는 한국 주식 종목 코드, 아니면 False

    Examples:
        >>> is_kr_stock_code('005930')
        True
        >>> is_kr_stock_code('KOSPI')
        False
        >>> is_kr_stock_code('AAPL')
        False
    """
    normalized = (code or '').strip().upper()
    if normalized in KR_INDEX_MAPPING:
        return False
    return bool(_KR_STOCK_PATTERN.match(normalized))


def get_kr_index_yf_symbol(code: str) -> tuple:
    """한국 지수의 Yahoo Finance 심볼과 한국어 이름을 반환합니다.

    Args:
        code: 사용자 입력, 예: 'KOSPI', '^KS11', 'KOSDAQ'

    Returns:
        (yf_symbol, korean_name) 튜플, 찾지 못하면 (None, None) 반환

    Examples:
        >>> get_kr_index_yf_symbol('KOSPI')
        ('^KS11', '코스피 종합지수')
        >>> get_kr_index_yf_symbol('AAPL')
        (None, None)
    """
    normalized = (code or '').strip().upper()
    return KR_INDEX_MAPPING.get(normalized, (None, None))

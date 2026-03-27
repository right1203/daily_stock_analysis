# data_provider/pykrx_fetcher.py
# -*- coding: utf-8 -*-
"""
===================================
한국 시장 데이터 소스 - pykrx
===================================

pykrx 라이브러리를 사용하여 KRX(한국거래소) 데이터를 가져옵니다.
KOSPI, KOSDAQ 종목의 일봉 데이터를 제공합니다.
"""

import logging
from typing import Optional

import pandas as pd

from data_provider.base import BaseFetcher, STANDARD_COLUMNS
from data_provider.kr_index_mapping import is_kr_stock_code, is_kr_index_code

logger = logging.getLogger(__name__)

_PYKRX_AVAILABLE = False
try:
    from pykrx import stock as pykrx_stock
    _PYKRX_AVAILABLE = True
except ImportError:
    logger.warning(
        "pykrx not installed; Korean market data unavailable. "
        "Run: pip install pykrx"
    )


class PykrxFetcher(BaseFetcher):
    """pykrx 기반 한국 시장 데이터 소스"""

    name = "pykrx"
    priority = 0

    def __init__(self):
        pass

    def supports(self, stock_code: str) -> bool:
        """한국 종목 코드(6자리 숫자)만 지원합니다. 지수는 yfinance로 처리."""
        return is_kr_stock_code(stock_code) and not is_kr_index_code(stock_code)

    def _fetch_raw_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        KRX에서 일봉 데이터를 가져옵니다.

        Args:
            stock_code: 6자리 종목 코드 (예: '005930')
            start_date: 시작일 (YYYY-MM-DD 형식)
            end_date: 종료일 (YYYY-MM-DD 형식)

        Returns:
            pykrx 원본 컬럼 형식의 DataFrame
        """
        if not _PYKRX_AVAILABLE:
            logger.warning("pykrx not available, skipping")
            return pd.DataFrame()

        # pykrx expects YYYYMMDD format without dashes
        start_str = start_date.replace("-", "")
        end_str = end_date.replace("-", "")

        df = pykrx_stock.get_market_ohlcv_by_date(start_str, end_str, stock_code)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        pykrx 컬럼을 표준 컬럼으로 변환합니다.

        pykrx columns: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률
        Standard columns: date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.reset_index()
        # pykrx returns index as '날짜' or datetime index; reset gives 'date' or '날짜'
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'date'})

        # Map Korean column names to standard names
        column_map = {
            '시가': 'open',
            '고가': 'high',
            '저가': 'low',
            '종가': 'close',
            '거래량': 'volume',
            '거래대금': 'amount',
            '등락률': 'pct_chg',
        }
        df = df.rename(columns=column_map)

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # Ensure all standard columns are present; fill missing with 0
        for col in STANDARD_COLUMNS:
            if col not in df.columns:
                df[col] = 0

        return df[STANDARD_COLUMNS]

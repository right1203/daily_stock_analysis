# -*- coding: utf-8 -*-
"""
===================================
YfinanceFetcher - US/global provider
===================================

Data source: Yahoo Finance via yfinance.

Key behavior:
1. Convert KR/US symbols to Yahoo Finance symbols.
2. Normalize Yahoo Finance response formats.
3. Retry transient connection failures with exponential backoff.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, STANDARD_COLUMNS
from .kr_index_mapping import get_kr_index_yf_symbol, is_kr_index_code, is_kr_stock_code
from .realtime_types import UnifiedRealtimeQuote, RealtimeSource
from .us_index_mapping import get_us_index_yf_symbol, is_us_index_code, is_us_stock_code

logger = logging.getLogger(__name__)


class YfinanceFetcher(BaseFetcher):
    """
    Yahoo Finance provider implementation.

    Priority: 1, after the Korean pykrx provider.
    Data source: Yahoo Finance.

    Notes:
    - Some symbols may have delayed or missing Yahoo Finance data.
    - Korean stock fallback uses the KOSPI suffix when no exchange suffix is supplied.
    """
    
    name = "YfinanceFetcher"
    priority = int(os.getenv("YFINANCE_PRIORITY", "1"))
    
    def __init__(self):
        """Initialize YfinanceFetcher."""
        pass

    def supports(self, stock_code: str) -> bool:
        """Return True for KR/US symbols supported by Yahoo Finance."""
        code = stock_code.strip().upper()
        return (
            is_us_index_code(code)
            or is_us_stock_code(code)
            or is_kr_index_code(code)
            or is_kr_stock_code(code)
            or code.endswith((".KS", ".KQ"))
        )
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        Convert a stock code to Yahoo Finance format.

        Yahoo Finance symbol formats:
        - US stocks: AAPL, TSLA, GOOGL
        - US indices: SPX -> ^GSPC
        - Korean indices: KOSPI -> ^KS11
        - Korean stocks: 005930 -> 005930.KS fallback

        Args:
            stock_code: Raw code such as '005930', 'KOSPI', or 'AAPL'.

        Returns:
            Yahoo Finance symbol.

        Examples:
            >>> fetcher._convert_stock_code('005930')
            '005930.KS'
            >>> fetcher._convert_stock_code('AAPL')
            'AAPL'
        """
        code = stock_code.strip().upper()

        yf_symbol, _ = get_us_index_yf_symbol(code)
        if yf_symbol:
            logger.debug(f"Detected US index: {code} -> {yf_symbol}")
            return yf_symbol

        yf_symbol, _ = get_kr_index_yf_symbol(code)
        if yf_symbol:
            logger.debug(f"Detected KR index: {code} -> {yf_symbol}")
            return yf_symbol

        if is_us_stock_code(code):
            logger.debug(f"Detected US stock: {code}")
            return code

        if is_kr_stock_code(code):
            return f"{code}.KS"

        if code.endswith((".KS", ".KQ")):
            return code

        raise DataFetchError(f"Unsupported market symbol for yfinance provider: {stock_code}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch raw data from Yahoo Finance.

        Uses yfinance.download() to fetch historical data.
        """
        import yfinance as yf
        
        # Convert code format.
        yf_code = self._convert_stock_code(stock_code)
        
        logger.debug(f"Calling yfinance.download({yf_code}, {start_date}, {end_date})")
        
        try:
            # Download data with yfinance.
            df = yf.download(
                tickers=yf_code,
                start=start_date,
                end=end_date,
                progress=False,  # Disable progress bar
                auto_adjust=True,  # Use adjusted prices
                multi_level_index=True
            )
            
            # Keep only yf_code columns to avoid mixing multiple tickers.
            if isinstance(df.columns, pd.MultiIndex) and len(df.columns) > 1:
                ticker_level = df.columns.get_level_values(1)
                mask = ticker_level == yf_code
                if mask.any():
                    df = df.loc[:, mask].copy()
                
            if df.empty:
                raise DataFetchError(f"Yahoo Finance returned no data for {stock_code}")
            
            return df
            
        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            raise DataFetchError(f"Yahoo Finance data fetch failed: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Normalize Yahoo Finance data.

        yfinance returns Open, High, Low, Close, and Volume columns with
        dates in the index. Newer yfinance versions may return MultiIndex
        columns such as ('Close', 'AMD'), which must be flattened first.

        Maps to standard columns:
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # Handle MultiIndex columns returned by newer yfinance versions.
        # Example: ('Close', 'AMD') -> 'Close'
        if isinstance(df.columns, pd.MultiIndex):
            logger.debug("Detected MultiIndex columns; flattening")
            # Keep first-level price columns: Close, High, Low, etc.
            df.columns = df.columns.get_level_values(0)
        
        # Reset index to make dates a column.
        df = df.reset_index()
        
        # Column mapping; yfinance uses title case.
        column_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Calculate percent change because yfinance does not provide it directly.
        if 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        
        # Estimate traded amount because yfinance does not provide it.
        # Amount is approximated as volume * close.
        if 'volume' in df.columns and 'close' in df.columns:
            df['amount'] = df['volume'] * df['close']
        else:
            df['amount'] = 0
        
        # Add stock code column.
        df['code'] = stock_code
        
        # Keep required columns only.
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df

    def _fetch_yf_ticker_data(self, yf, yf_code: str, name: str, return_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch quote data for a single index or stock via yfinance.

        Args:
            yf: yfinance module reference.
            yf_code: Yahoo Finance symbol, such as '^GSPC' or 'AAPL'.
            name: Index display name.
            return_code: code field written to the result dict, such as 'SPX'.

        Returns:
            Quote dictionary, or None on failure.
        """
        ticker = yf.Ticker(yf_code)
        # Fetch two recent days to calculate percent change.
        hist = ticker.history(period='2d')
        if hist.empty:
            return None
        today_row = hist.iloc[-1]
        prev_row = hist.iloc[-2] if len(hist) > 1 else today_row
        price = float(today_row['Close'])
        prev_close = float(prev_row['Close'])
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        high = float(today_row['High'])
        low = float(today_row['Low'])
        # Amplitude = (high - low) / previous close * 100.
        amplitude = ((high - low) / prev_close * 100) if prev_close else 0
        return {
            'code': return_code,
            'name': name,
            'current': price,
            'change': change,
            'change_pct': change_pct,
            'open': float(today_row['Open']),
            'high': high,
            'low': low,
            'prev_close': prev_close,
            'volume': float(today_row['Volume']),
            'amount': 0.0,  # Yahoo Finance does not provide accurate traded amount
            'amplitude': amplitude,
        }

    def get_main_indices(self, region: str = "kr") -> Optional[List[Dict[str, Any]]]:
        """
        Get major KR/US index quotes from Yahoo Finance.
        """
        import yfinance as yf

        if region == "us":
            return self._get_us_main_indices(yf)
        if region == "kr":
            return self._get_kr_main_indices(yf)
        return None

    def _get_kr_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get Korean major index quotes from Yahoo Finance."""
        kr_indices = ["KOSPI", "KOSDAQ", "KOSPI200"]
        results = []
        try:
            for code in kr_indices:
                yf_symbol, name = get_kr_index_yf_symbol(code)
                if not yf_symbol:
                    continue
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Korean index {name} fetched")
                except Exception as e:
                    logger.warning(f"[Yfinance] Korean index {name} failed: {e}")

            if results:
                logger.info(f"[Yfinance] Fetched {len(results)} Korean index quotes")
                return results

        except Exception as e:
            logger.error(f"[Yfinance] Korean index quotes failed: {e}")

        return None

    def _get_us_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get major US index quotes (SPX, IXIC, DJI, VIX)."""
        # Core US indices required for market review.
        us_indices = ['SPX', 'IXIC', 'DJI', 'VIX']
        results = []
        try:
            for code in us_indices:
                yf_symbol, name = get_us_index_yf_symbol(code)
                if not yf_symbol:
                    continue
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] US index {name} fetched")
                except Exception as e:
                    logger.warning(f"[Yfinance] US index {name} failed: {e}")

            if results:
                logger.info(f"[Yfinance] Fetched {len(results)} US index quotes")
                return results

        except Exception as e:
            logger.error(f"[Yfinance] US index quotes failed: {e}")

        return None

    def _is_us_stock(self, stock_code: str) -> bool:
        """
        Return whether the code is a US stock, excluding US indices.

        Delegates to is_us_stock_code() in us_index_mapping.
        """
        return is_us_stock_code(stock_code)

    def _get_us_index_realtime_quote(
        self,
        user_code: str,
        yf_symbol: str,
        index_name: str,
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        Get realtime quote for US index (e.g. SPX -> ^GSPC).

        Args:
            user_code: User input code (e.g. SPX)
            yf_symbol: Yahoo Finance symbol (e.g. ^GSPC)
            index_name: Display name for the index.

        Returns:
            UnifiedRealtimeQuote or None
        """
        import yfinance as yf

        try:
            logger.debug(f"[Yfinance] Fetching US index realtime quote {user_code} ({yf_symbol})")
            ticker = yf.Ticker(yf_symbol)

            try:
                info = ticker.fast_info
                if info is None:
                    raise ValueError("fast_info is None")
                price = getattr(info, 'lastPrice', None) or getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previousClose', None) or getattr(info, 'previous_close', None)
                open_price = getattr(info, 'open', None)
                high = getattr(info, 'dayHigh', None) or getattr(info, 'day_high', None)
                low = getattr(info, 'dayLow', None) or getattr(info, 'day_low', None)
                volume = getattr(info, 'lastVolume', None) or getattr(info, 'last_volume', None)
            except Exception:
                logger.debug("[Yfinance] fast_info failed; trying history method")
                hist = ticker.history(period='2d')
                if hist.empty:
                    logger.warning(f"[Yfinance] Unable to fetch data for {yf_symbol}")
                    return None
                today = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else today
                price = float(today['Close'])
                prev_close = float(prev['Close'])
                open_price = float(today['Open'])
                high = float(today['High'])
                low = float(today['Low'])
                volume = int(today['Volume'])

            change_amount = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100

            amplitude = None
            if high is not None and low is not None and prev_close is not None and prev_close > 0:
                amplitude = ((high - low) / prev_close) * 100

            quote = UnifiedRealtimeQuote(
                code=user_code,
                name=index_name or user_code,
                source=RealtimeSource.YFINANCE,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=None,
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,
                pb_ratio=None,
                total_mv=None,
                circ_mv=None,
            )
            logger.info(f"[Yfinance] US index {user_code} realtime quote fetched: price={price}")
            return quote
        except Exception as e:
            logger.warning(f"[Yfinance] US index {user_code} realtime quote failed: {e}")
            return None

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get realtime quote data for US stocks and US indices.

        Supports US stocks such as AAPL and TSLA, and US indices such as
        SPX and DJI. Data source: yfinance Ticker.info.

        Args:
            stock_code: US stock or index code, such as 'AMD', 'AAPL', 'SPX', 'DJI'.

        Returns:
            UnifiedRealtimeQuote object, or None on failure.
        """
        import yfinance as yf

        # US indices use mapping such as SPX -> ^GSPC.
        yf_symbol, index_name = get_us_index_yf_symbol(stock_code)
        if yf_symbol:
            return self._get_us_index_realtime_quote(
                user_code=stock_code.strip().upper(),
                yf_symbol=yf_symbol,
                index_name=index_name,
            )

        # Handle US stocks only.
        if not self._is_us_stock(stock_code):
            logger.debug(f"[Yfinance] {stock_code} is not a US stock; skipping")
            return None

        try:
            symbol = stock_code.strip().upper()
            logger.debug(f"[Yfinance] Fetching US stock realtime quote {symbol}")
            
            ticker = yf.Ticker(symbol)
            
            # Try fast_info first; it is faster but has fewer fields.
            try:
                info = ticker.fast_info
                if info is None:
                    raise ValueError("fast_info is None")
                
                price = getattr(info, 'lastPrice', None) or getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previousClose', None) or getattr(info, 'previous_close', None)
                open_price = getattr(info, 'open', None)
                high = getattr(info, 'dayHigh', None) or getattr(info, 'day_high', None)
                low = getattr(info, 'dayLow', None) or getattr(info, 'day_low', None)
                volume = getattr(info, 'lastVolume', None) or getattr(info, 'last_volume', None)
                market_cap = getattr(info, 'marketCap', None) or getattr(info, 'market_cap', None)
                
            except Exception:
                # Fallback to history for the latest data.
                logger.debug("[Yfinance] fast_info failed; trying history method")
                hist = ticker.history(period='2d')
                if hist.empty:
                    logger.warning(f"[Yfinance] Unable to fetch data for {symbol}")
                    return None
                
                today = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else today
                
                price = float(today['Close'])
                prev_close = float(prev['Close'])
                open_price = float(today['Open'])
                high = float(today['High'])
                low = float(today['Low'])
                volume = int(today['Volume'])
                market_cap = None
            
            # Calculate percent change.
            change_amount = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100
            
            # Calculate amplitude.
            amplitude = None
            if high is not None and low is not None and prev_close is not None and prev_close > 0:
                amplitude = ((high - low) / prev_close) * 100
            
            # Get stock name.
            try:
                name = ticker.info.get('shortName', '') or ticker.info.get('longName', '') or symbol
            except Exception:
                name = symbol
            
            quote = UnifiedRealtimeQuote(
                code=symbol,
                name=name,
                source=RealtimeSource.YFINANCE,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=None,  # yfinance does not provide traded amount directly
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,
                pb_ratio=None,
                total_mv=market_cap,
                circ_mv=None,
            )
            
            logger.info(f"[Yfinance] US stock {symbol} realtime quote fetched: price={price}")
            return quote
            
        except Exception as e:
            logger.warning(f"[Yfinance] US stock {stock_code} realtime quote failed: {e}")
            return None


if __name__ == "__main__":
    # Smoke test code.
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = YfinanceFetcher()
    
    try:
        df = fetcher.get_daily_data('AAPL')
        print(f"fetch succeeded, rows={len(df)}")
        print(df.tail())
    except Exception as e:
        print(f"fetch failed: {e}")

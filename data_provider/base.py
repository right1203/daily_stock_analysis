# -*- coding: utf-8 -*-
"""
===================================
데이터 소스 기본 클래스 및 관리자
===================================

디자인 패턴: 전략 패턴 (Strategy Pattern)
- BaseFetcher: 추상 기본 클래스, 통합 인터페이스 정의
- DataFetcherManager: 전략 관리자, 자동 전환 구현

차단 방지 전략:
1. 각 Fetcher 내장 흐름 제어 로직
2. 실패 시 자동으로 다음 데이터 소스로 전환
3. 지수 백오프 재시도 메커니즘
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.analyzer import STOCK_NAME_MAP

# Configure logging.
logger = logging.getLogger(__name__)


# === Standardized column definitions ===
STANDARD_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']


def unwrap_exception(exc: Exception) -> Exception:
    """
    Follow chained exceptions and return the deepest non-cyclic cause.
    """
    current = exc
    visited = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))
        next_exc = current.__cause__ or current.__context__
        if next_exc is None:
            break
        current = next_exc

    return current


def summarize_exception(exc: Exception) -> Tuple[str, str]:
    """
    Build a stable summary for logs while preserving the application-layer message.
    """
    root = unwrap_exception(exc)
    error_type = type(root).__name__
    message = str(exc).strip() or str(root).strip() or error_type
    return error_type, " ".join(message.split())


def normalize_stock_code(stock_code: str) -> str:
    """
    Normalize stock code by stripping exchange prefixes/suffixes.

    Accepted formats and their normalized results:
    - '005930'      -> '005930'   (already clean Korean stock)
    - 'KR005930'    -> '005930'   (strip KR prefix)
    - 'kr005930'    -> '005930'   (case-insensitive)
    - '005930.KS'   -> '005930'   (strip .KS KOSPI suffix)
    - '035720.KQ'   -> '035720'   (strip .KQ KOSDAQ suffix)
    - 'AAPL'        -> 'AAPL'     (keep US stock ticker as-is)
    - 'BRK.B'       -> 'BRK.B'   (US stock with class suffix, unchanged)

    This function is applied at the DataProviderManager layer so that
    all individual fetchers receive a clean numeric code (for KR stocks/ETFs).
    """
    code = stock_code.strip()
    upper = code.upper()

    # Strip KR prefix (e.g. KR005930 -> 005930, kr005930 -> 005930)
    if upper.startswith('KR') and not upper.startswith('KR.'):
        candidate = code[2:]
        if candidate.isdigit() and len(candidate) in (5, 6):
            return candidate

    # Strip .KS/.KQ suffix (e.g. 005930.KS -> 005930, 035720.KQ -> 035720)
    if '.' in code:
        base, suffix = code.rsplit('.', 1)
        if suffix.upper() in ('KS', 'KQ') and base.isdigit():
            return base

    return code


def canonical_stock_code(code: str) -> str:
    """
    Return the canonical (uppercase) form of a stock code.

    This is a display/storage layer concern, distinct from normalize_stock_code
    which strips exchange prefixes. Apply at system input boundaries to ensure
    consistent case across BOT, WEB UI, API, and CLI paths (Issue #355).

    Examples:
        'aapl'    -> 'AAPL'
        'AAPL'    -> 'AAPL'
        '005930'  -> '005930'  (digits are unchanged)
    """
    return (code or "").strip().upper()


class DataFetchError(Exception):
    """Base exception for data fetch failures."""
    pass


class RateLimitError(DataFetchError):
    """API rate limit exception."""
    pass


class DataSourceUnavailableError(DataFetchError):
    """Data source unavailable exception."""
    pass


class BaseFetcher(ABC):
    """
    Abstract base class for market data fetchers.

    Responsibilities:
    1. Define a unified data fetch interface.
    2. Provide data normalization helpers.
    3. Implement common technical indicator calculations.

    Subclasses implement:
    - _fetch_raw_data(): fetch raw data from a concrete source.
    - _normalize_data(): convert raw data to the standard schema.
    """
    
    name: str = "BaseFetcher"
    priority: int = 99  # Lower numbers have higher priority.
    
    @abstractmethod
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch raw data from a provider. Subclasses must implement this.
        
        Args:
            stock_code: Stock code, e.g. '005930', '035720', 'AAPL'
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            
        Returns:
            Raw DataFrame with provider-specific columns.
        """
        pass
    
    @abstractmethod
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Normalize data column names. Subclasses must implement this.

        Normalize provider-specific column names to:
        ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        """
        pass

    def get_main_indices(self, region: str = "kr") -> Optional[List[Dict[str, Any]]]:
        """
        Get major index quotes.

        Args:
            region: Market region, either kr or us.

        Returns:
            List[Dict]: Index entries with code, name, current, change,
                change_pct, volume, and amount fields.
        """
        return None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get market breadth statistics.

        Returns:
            Dict with up, down, flat, limit-up, limit-down, and total amount counts.
        """
        return None

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """
        Get sector gain/loss rankings.

        Args:
            n: Number of top entries to return.

        Returns:
            Tuple of leading and lagging sector lists.
        """
        return None

    def get_daily_data(
        self,
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Get daily price data through the unified fetcher entrypoint.
        
        Args:
            stock_code: Stock code.
            start_date: Optional start date.
            end_date: Optional end date, defaults to today.
            days: Number of days used when start_date is omitted.
            
        Returns:
            Standardized DataFrame with technical indicators.
        """
        # Compute date range.
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            # Over-fetch by calendar days to cover recent trading days.
            from datetime import timedelta
            start_dt = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days * 2)
            start_date = start_dt.strftime('%Y-%m-%d')

        request_start = time.time()
        logger.info(f"[{self.name}] Fetching daily data for {stock_code}: range={start_date} ~ {end_date}")
        
        try:
            # Step 1: fetch raw data.
            raw_df = self._fetch_raw_data(stock_code, start_date, end_date)
            
            if raw_df is None or raw_df.empty:
                raise DataFetchError(f"[{self.name}] No data returned for {stock_code}")
            
            # Step 2: normalize column names.
            df = self._normalize_data(raw_df, stock_code)
            
            # Step 3: clean data.
            df = self._clean_data(df)
            
            # Step 4: calculate technical indicators.
            df = self._calculate_indicators(df)

            elapsed = time.time() - request_start
            logger.info(
                f"[{self.name}] {stock_code} fetched successfully: range={start_date} ~ {end_date}, "
                f"rows={len(df)}, elapsed={elapsed:.2f}s"
            )
            return df
            
        except Exception as e:
            elapsed = time.time() - request_start
            error_type, error_reason = summarize_exception(e)
            logger.error(
                f"[{self.name}] {stock_code} fetch failed: range={start_date} ~ {end_date}, "
                f"error_type={error_type}, elapsed={elapsed:.2f}s, reason={error_reason}"
            )
            raise DataFetchError(f"[{self.name}] {stock_code}: {error_reason}") from e
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean data before indicator calculation.
        """
        df = df.copy()
        
        # Ensure the date column uses datetime type.
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        # Convert numeric columns.
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows missing key fields.
        df = df.dropna(subset=['close', 'volume'])
        
        # Sort by date ascending.
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators.

        Indicators:
        - MA5, MA10, MA20: moving averages.
        - Volume_Ratio: daily volume divided by the 5-day average volume.
        """
        df = df.copy()
        
        # Moving averages.
        df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        
        # Daily volume divided by the previous 5-day average volume.
        # This is closer to a volume expansion ratio than intraday volume ratio.
        # Keep the existing behavior unchanged.
        avg_volume_5 = df['volume'].rolling(window=5, min_periods=1).mean()
        df['volume_ratio'] = df['volume'] / avg_volume_5.shift(1)
        df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
        
        # Keep two decimal places.
        for col in ['ma5', 'ma10', 'ma20', 'volume_ratio']:
            if col in df.columns:
                df[col] = df[col].round(2)
        
        return df
    
    @staticmethod
    def random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        Random jitter sleep between provider requests.
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Random sleep for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)


class DataFetcherManager:
    """
    Data source strategy manager.

    Manages fetcher priority, failover, and the unified data access interface.
    """
    
    def __init__(self, fetchers: Optional[List[BaseFetcher]] = None):
        """
        Initialize the manager.
        
        Args:
            fetchers: Optional fetcher list. Defaults are initialized by priority.
        """
        self._fetchers: List[BaseFetcher] = []
        
        if fetchers:
            # Sort by priority.
            self._fetchers = sorted(fetchers, key=lambda f: f.priority)
        else:
            # Default providers are loaded lazily.
            self._init_default_fetchers()
    
    def _init_default_fetchers(self) -> None:
        """
        Initialize the default Korea/US provider list.

        Default order:
        1. PykrxFetcher for Korean listed stocks.
        2. YfinanceFetcher for US stocks, US indices, and global index fallback.
        """
        from .pykrx_fetcher import PykrxFetcher
        from .yfinance_fetcher import YfinanceFetcher

        self._fetchers = [
            PykrxFetcher(),
            YfinanceFetcher(),
        ]
        self._fetchers.sort(key=lambda f: f.priority)

        priority_info = ", ".join([f"{f.name}(P{f.priority})" for f in self._fetchers])
        logger.info(f"Initialized {len(self._fetchers)} KR/US data fetchers: {priority_info}")

    @staticmethod
    def _fetcher_supports(fetcher: BaseFetcher, stock_code: str) -> bool:
        supports = getattr(fetcher, "supports", None)
        if callable(supports):
            return bool(supports(stock_code))
        return True
    
    def add_fetcher(self, fetcher: BaseFetcher) -> None:
        """Add a fetcher and re-sort by priority."""
        self._fetchers.append(fetcher)
        self._fetchers.sort(key=lambda f: f.priority)
    
    def get_daily_data(
        self, 
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> Tuple[pd.DataFrame, str]:
        """
        Get daily data with automatic provider failover.
        
        Args:
            stock_code: Stock code.
            start_date: Start date.
            end_date: End date.
            days: Number of days.
            
        Returns:
            Tuple[DataFrame, str]: data and successful provider name.
            
        Raises:
            DataFetchError: Raised when all providers fail.
        """
        from .kr_index_mapping import is_kr_index_code
        from .us_index_mapping import is_us_index_code, is_us_stock_code

        raw_stock_code = stock_code.strip()
        raw_upper_code = raw_stock_code.upper()
        explicit_yfinance_kr_symbol = (
            "." in raw_upper_code
            and raw_upper_code.rsplit(".", 1)[1] in ("KS", "KQ")
            and raw_upper_code.rsplit(".", 1)[0].isdigit()
        )

        # Normalize code for primary KR providers.
        stock_code = normalize_stock_code(stock_code)

        errors = []
        total_fetchers = len(self._fetchers)
        request_start = time.time()

        # Route index and US symbols directly to yfinance.
        if is_us_index_code(stock_code) or is_us_stock_code(stock_code) or is_kr_index_code(stock_code):
            for attempt, fetcher in enumerate(self._fetchers, start=1):
                if fetcher.name == "YfinanceFetcher":
                    try:
                        logger.info(
                            f"[Data source attempt {attempt}/{total_fetchers}] [{fetcher.name}] "
                            f"KR/US symbol {stock_code} direct route..."
                        )
                        df = fetcher.get_daily_data(
                            stock_code=stock_code,
                            start_date=start_date,
                            end_date=end_date,
                            days=days,
                        )
                        if df is not None and not df.empty:
                            elapsed = time.time() - request_start
                            logger.info(
                                f"[Data source complete] {stock_code} fetched via [{fetcher.name}]: "
                                f"rows={len(df)}, elapsed={elapsed:.2f}s"
                            )
                            return df, fetcher.name
                    except Exception as e:
                        error_type, error_reason = summarize_exception(e)
                        error_msg = f"[{fetcher.name}] ({error_type}) {error_reason}"
                        logger.warning(
                            f"[Data source failed {attempt}/{total_fetchers}] [{fetcher.name}] {stock_code}: "
                            f"error_type={error_type}, reason={error_reason}"
                        )
                        errors.append(error_msg)
                    break
            # YfinanceFetcher failed or not found
            error_summary = f"KR/US symbol {stock_code} fetch failed:\n" + "\n".join(errors)
            elapsed = time.time() - request_start
            logger.error(f"[Data source aborted] {stock_code} fetch failed: elapsed={elapsed:.2f}s\n{error_summary}")
            raise DataFetchError(error_summary)

        for attempt, fetcher in enumerate(self._fetchers, start=1):
            if not self._fetcher_supports(fetcher, stock_code):
                logger.debug(f"[Data source skipped {attempt}/{total_fetchers}] [{fetcher.name}] unsupported {stock_code}")
                continue

            try:
                fetch_stock_code = raw_upper_code if fetcher.name == "YfinanceFetcher" and explicit_yfinance_kr_symbol else stock_code
                logger.info(f"[Data source attempt {attempt}/{total_fetchers}] [{fetcher.name}] fetching {fetch_stock_code}...")
                df = fetcher.get_daily_data(
                    stock_code=fetch_stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    days=days
                )
                
                if df is not None and not df.empty:
                    elapsed = time.time() - request_start
                    logger.info(
                        f"[Data source complete] {stock_code} fetched via [{fetcher.name}]: "
                        f"rows={len(df)}, elapsed={elapsed:.2f}s"
                    )
                    return df, fetcher.name
                    
            except Exception as e:
                error_type, error_reason = summarize_exception(e)
                error_msg = f"[{fetcher.name}] ({error_type}) {error_reason}"
                logger.warning(
                    f"[Data source failed {attempt}/{total_fetchers}] [{fetcher.name}] {stock_code}: "
                    f"error_type={error_type}, reason={error_reason}"
                )
                errors.append(error_msg)
                if attempt < total_fetchers:
                    next_fetcher = self._fetchers[attempt]
                    logger.info(f"[Data source switch] {stock_code}: [{fetcher.name}] -> [{next_fetcher.name}]")
                # Continue with the next provider.
                continue
        
        # All providers failed.
        error_summary = f"All data sources failed for {stock_code}:\n" + "\n".join(errors)
        elapsed = time.time() - request_start
        logger.error(f"[Data source aborted] {stock_code} fetch failed: elapsed={elapsed:.2f}s\n{error_summary}")
        raise DataFetchError(error_summary)
    
    @property
    def available_fetchers(self) -> List[str]:
        """Return available fetcher names."""
        return [f.name for f in self._fetchers]
    
    def prefetch_realtime_quotes(self, stock_codes: List[str]) -> int:
        """
        Return 0 because the KR/US provider set has no bulk realtime prefetch source.

        Args:
            stock_codes: Stock codes pending analysis.
            
        Returns:
            Always 0.
        """
        if stock_codes:
            logger.debug("[Realtime prefetch] No KR/US bulk realtime source is configured; skipping")
        return 0
    
    def get_realtime_quote(self, stock_code: str):
        """
        Get realtime quote data from the remaining KR/US provider layer.

        yfinance supports US realtime quotes and index quotes. Korean realtime
        quotes are not available through the remaining runtime providers.
        
        Args:
            stock_code: Stock code.
            
        Returns:
            UnifiedRealtimeQuote when available, otherwise None.
        """
        stock_code = normalize_stock_code(stock_code)

        from .us_index_mapping import is_us_index_code, is_us_stock_code
        from src.config import get_config

        config = get_config()

        if not config.enable_realtime_quote:
            logger.debug(f"[Realtime quote] Feature disabled; skipping {stock_code}")
            return None

        if is_us_index_code(stock_code) or is_us_stock_code(stock_code):
            for fetcher in self._fetchers:
                if fetcher.name == "YfinanceFetcher":
                    if hasattr(fetcher, 'get_realtime_quote'):
                        try:
                            quote = fetcher.get_realtime_quote(stock_code)
                            if quote is not None:
                                logger.info(f"[Realtime quote] {stock_code} fetched via yfinance")
                                return quote
                        except Exception as e:
                            logger.warning(f"[Realtime quote] yfinance failed for {stock_code}: {e}")
                    break
            logger.warning(f"[Realtime quote] No available source for {stock_code}")
            return None

        logger.debug(f"[Realtime quote] Unsupported realtime market for {stock_code}")
        return None

    # Fields worth supplementing from secondary sources when the primary
    # source returns None for them. Ordered by importance.
    _SUPPLEMENT_FIELDS = [
        'volume_ratio', 'turnover_rate',
        'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv',
        'amplitude',
    ]

    @classmethod
    def _quote_needs_supplement(cls, quote) -> bool:
        """Check if any key supplementary field is still None."""
        for f in cls._SUPPLEMENT_FIELDS:
            if getattr(quote, f, None) is None:
                return True
        return False

    @classmethod
    def _merge_quote_fields(cls, primary, secondary) -> list:
        """
        Copy non-None fields from *secondary* into *primary* where
        *primary* has None. Returns list of field names that were filled.
        """
        filled = []
        for f in cls._SUPPLEMENT_FIELDS:
            if getattr(primary, f, None) is None:
                val = getattr(secondary, f, None)
                if val is not None:
                    setattr(primary, f, val)
                    filled.append(f)
        return filled

    def get_chip_distribution(self, stock_code: str):
        """
        Return None because chip distribution providers were removed.

        Args:
            stock_code: Stock code.

        Returns:
            Always None.
        """
        stock_code = normalize_stock_code(stock_code)
        logger.debug(f"[Chip distribution] No KR/US provider available for {stock_code}")
        return None

    def get_stock_name(self, stock_code: str, allow_realtime: bool = True) -> Optional[str]:
        """
        Get a stock display name with provider failover.
        
        Args:
            stock_code: Stock code.
            allow_realtime: Whether to query realtime quote first. Set False when
                caller only wants lightweight prefetch without triggering heavy
                realtime source calls.
            
        Returns:
            Stock name, or an empty string when all providers fail.
        """
        # Normalize code (strip SH/SZ prefix etc.)
        stock_code = normalize_stock_code(stock_code)
        if stock_code in STOCK_NAME_MAP:
            return STOCK_NAME_MAP[stock_code]

        # 1. Check cache first.
        if hasattr(self, '_stock_name_cache') and stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]
        
        # Initialize cache.
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
        
        # 2. Try realtime quote when enabled by the caller.
        if allow_realtime:
            quote = self.get_realtime_quote(stock_code)
            if quote and hasattr(quote, 'name') and quote.name:
                name = quote.name
                self._stock_name_cache[stock_code] = name
                logger.info(f"[Stock name] from realtime quote: {stock_code} -> {name}")
                return name

        # 3. Try each provider.
        for fetcher in self._fetchers:
            if hasattr(fetcher, 'get_stock_name'):
                try:
                    name = fetcher.get_stock_name(stock_code)
                    if name:
                        self._stock_name_cache[stock_code] = name
                        logger.info(f"[Stock name] from {fetcher.name}: {stock_code} -> {name}")
                        return name
                except Exception as e:
                    logger.debug(f"[Stock name] {fetcher.name} failed: {e}")
                    continue
        
        # 4. All providers failed.
        logger.warning(f"[Stock name] all providers failed for {stock_code}")
        return ""

    def prefetch_stock_names(self, stock_codes: List[str], use_bulk: bool = False) -> None:
        """
        Pre-fetch stock names into cache before parallel analysis (Issue #455).

        When use_bulk=False, only calls get_stock_name per code (no get_stock_list),
        avoiding full-market fetch. Sequential execution to avoid rate limits.

        Args:
            stock_codes: Stock codes to prefetch.
            use_bulk: If True, may use get_stock_list (full fetch). Default False.
        """
        if not stock_codes:
            return
        stock_codes = [normalize_stock_code(c) for c in stock_codes]
        if use_bulk:
            self.batch_get_stock_names(stock_codes)
            return
        for code in stock_codes:
            # Skip realtime lookup to avoid triggering expensive full-market quote
            # requests during the prefetch phase.
            self.get_stock_name(code, allow_realtime=False)

    def batch_get_stock_names(self, stock_codes: List[str]) -> Dict[str, str]:
        """
        Get stock names in batch.
        
        Args:
            stock_codes: Stock codes.
            
        Returns:
            Mapping of stock code to stock name.
        """
        result = {}
        missing_codes = set(stock_codes)
        
        # 1. Check cache first.
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
        
        for code in stock_codes:
            if code in self._stock_name_cache:
                result[code] = self._stock_name_cache[code]
                missing_codes.discard(code)
        
        if not missing_codes:
            return result
        
        # 2. Try provider bulk stock list APIs.
        for fetcher in self._fetchers:
            if hasattr(fetcher, 'get_stock_list') and missing_codes:
                try:
                    stock_list = fetcher.get_stock_list()
                    if stock_list is not None and not stock_list.empty:
                        for _, row in stock_list.iterrows():
                            code = row.get('code')
                            name = row.get('name')
                            if code and name:
                                self._stock_name_cache[code] = name
                                if code in missing_codes:
                                    result[code] = name
                                    missing_codes.discard(code)
                        
                        if not missing_codes:
                            break
                        
                        logger.info(
                            f"[Stock name] batch fetch from {fetcher.name} complete; "
                            f"{len(missing_codes)} remaining"
                        )
                except Exception as e:
                    logger.debug(f"[Stock name] {fetcher.name} batch fetch failed: {e}")
                    continue
        
        # 3. Fetch remaining names individually.
        for code in list(missing_codes):
            name = self.get_stock_name(code)
            if name:
                result[code] = name
                missing_codes.discard(code)
        
        logger.info(f"[Stock name] batch fetch complete: {len(result)}/{len(stock_codes)}")
        return result

    def get_main_indices(self, region: str = "kr") -> List[Dict[str, Any]]:
        """Get major market indices through the remaining provider layer."""
        for fetcher in self._fetchers:
            try:
                data = fetcher.get_main_indices(region=region)
                if data:
                    logger.info(f"[{fetcher.name}] index quote fetch succeeded")
                    return data
            except Exception as e:
                logger.warning(f"[{fetcher.name}] index quote fetch failed: {e}")
                continue
        return []

    def get_market_stats(self) -> Dict[str, Any]:
        """Get market breadth statistics with provider failover."""
        for fetcher in self._fetchers:
            try:
                data = fetcher.get_market_stats()
                if data:
                    logger.info(f"[{fetcher.name}] market statistics fetch succeeded")
                    return data
            except Exception as e:
                logger.warning(f"[{fetcher.name}] market statistics fetch failed: {e}")
                continue
        return {}

    def get_sector_rankings(self, n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """Get sector rankings with provider failover."""
        for fetcher in self._fetchers:
            try:
                data = fetcher.get_sector_rankings(n)
                if data:
                    logger.info(f"[{fetcher.name}] sector ranking fetch succeeded")
                    return data
            except Exception as e:
                logger.warning(f"[{fetcher.name}] sector ranking fetch failed: {e}")
                continue
        return [], []

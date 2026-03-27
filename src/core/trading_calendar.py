# -*- coding: utf-8 -*-
"""
===================================
거래 캘린더 모듈 (Issue #373)
===================================

역할:
1. 시장별 (한국/미국) 당일 거래일 여부 판단
2. 시장 시간대 기준 '오늘' 날짜 취득 (서버 UTC 오류 방지)
3. per-stock 필터링 지원: 당일 개장된 시장의 종목만 분석

의존성: exchange-calendars (선택 사항, 사용 불가 시 fail-open)
"""

import logging
from datetime import date, datetime
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Exchange-calendars availability
_XCALS_AVAILABLE = False
try:
    import exchange_calendars as xcals
    _XCALS_AVAILABLE = True
except ImportError:
    logger.warning(
        "exchange-calendars not installed; trading day check disabled. "
        "Run: pip install exchange-calendars"
    )

# Market -> exchange code (exchange-calendars)
MARKET_EXCHANGE = {"kr": "XKRX", "us": "XNYS"}

# Market -> IANA timezone for "today"
MARKET_TIMEZONE = {
    "kr": "Asia/Seoul",
    "us": "America/New_York",
}


def get_market_for_stock(code: str) -> Optional[str]:
    """
    Infer market region for a stock code.

    Returns:
        'kr' | 'us' | None (None = unrecognized, fail-open: treat as open)
    """
    if not code or not isinstance(code, str):
        return None
    code = (code or "").strip().upper()

    from data_provider import is_us_stock_code, is_us_index_code
    from data_provider.kr_index_mapping import is_kr_index_code, is_kr_stock_code

    # Check KR indices first: known KR symbols like KOSPI would otherwise
    # match the generic US-stock regex (1-5 uppercase letters).
    if is_kr_index_code(code) or is_kr_stock_code(code):
        return "kr"
    if is_us_stock_code(code) or is_us_index_code(code):
        return "us"
    return None


def is_market_open(market: str, check_date: date) -> bool:
    """
    Check if the given market is open on the given date.

    Fail-open: returns True if exchange-calendars unavailable or date out of range.

    Args:
        market: 'kr' | 'us'
        check_date: Date to check

    Returns:
        True if trading day (or fail-open), False otherwise
    """
    if not _XCALS_AVAILABLE:
        return True
    ex = MARKET_EXCHANGE.get(market)
    if not ex:
        return True
    try:
        cal = xcals.get_calendar(ex)
        session = datetime(check_date.year, check_date.month, check_date.day)
        return cal.is_session(session)
    except Exception as e:
        logger.warning("trading_calendar.is_market_open fail-open: %s", e)
        return True


def get_open_markets_today() -> Set[str]:
    """
    Get markets that are open today (by each market's local timezone).

    Returns:
        Set of market keys ('kr', 'us') that are trading today
    """
    if not _XCALS_AVAILABLE:
        return {"kr", "us"}
    result: Set[str] = set()
    from zoneinfo import ZoneInfo
    for mkt, tz_name in MARKET_TIMEZONE.items():
        try:
            tz = ZoneInfo(tz_name)
            today = datetime.now(tz).date()
            if is_market_open(mkt, today):
                result.add(mkt)
        except Exception as e:
            logger.warning("get_open_markets_today fail-open for %s: %s", mkt, e)
            result.add(mkt)
    return result


def compute_effective_region(
    config_region: str, open_markets: Set[str]
) -> Optional[str]:
    """
    Compute effective market review region given config and open markets.

    Args:
        config_region: From MARKET_REVIEW_REGION ('kr' | 'us' | 'both')
        open_markets: Markets open today

    Returns:
        None: caller uses config default (check disabled)
        '': all relevant markets closed, skip market review
        'kr' | 'us' | 'both': effective subset for today
    """
    if config_region not in ("kr", "us", "both"):
        config_region = "kr"
    if config_region == "kr":
        return "kr" if "kr" in open_markets else ""
    if config_region == "us":
        return "us" if "us" in open_markets else ""
    # both
    parts = []
    if "kr" in open_markets:
        parts.append("kr")
    if "us" in open_markets:
        parts.append("us")
    if not parts:
        return ""
    return "both" if len(parts) == 2 else parts[0]

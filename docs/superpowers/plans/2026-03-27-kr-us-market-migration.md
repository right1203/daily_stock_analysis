# KR+US Market Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Chinese market (A-shares, HK) support with Korean market (KOSPI/KOSDAQ) support, keeping US market intact. Translate all Chinese UI/prompts to Korean.

**Architecture:** The existing market abstraction (`MarketProfile`, `MarketStrategyBlueprint`, `trading_calendar`) already separates market-specific logic into pluggable components. We add `kr` as a new market region, replace `cn`/`hk` defaults with `kr`/`us`, add a Korean data fetcher (`pykrx` + `yfinance`), translate all Chinese strings to Korean, and update the LLM system prompt for Korean market analysis.

**Tech Stack:** Python 3.11, FastAPI, pykrx (Korean exchange data), yfinance (US + KR fallback), exchange-calendars (KRX), LiteLLM

---

## Scope Check

This is a single cohesive migration — all changes are interdependent (market detection feeds into data fetching, which feeds into analysis, which feeds into notifications). One plan is appropriate.

## File Structure

### Files to Create
| File | Responsibility |
|------|---------------|
| `data_provider/kr_index_mapping.py` | Korean index code mapping (KOSPI, KOSDAQ → Yahoo Finance symbols) |
| `data_provider/pykrx_fetcher.py` | Korean market data fetcher using pykrx library |
| `tests/test_kr_index_mapping.py` | Tests for Korean index mapping |
| `tests/test_kr_stock_detection.py` | Tests for Korean stock code detection |
| `tests/test_pykrx_fetcher.py` | Tests for pykrx data fetcher |
| `tests/test_kr_market_profile.py` | Tests for KR market profile and strategy |
| `tests/test_kr_trading_calendar.py` | Tests for KRX trading calendar |

### Files to Modify
| File | What Changes |
|------|-------------|
| `data_provider/base.py` | Add `is_kr_stock_code()`, update `normalize_stock_code()` for KR prefix |
| `data_provider/us_index_mapping.py` | Translate Chinese index names to Korean |
| `data_provider/__init__.py` | Export KR functions, add PykrxFetcher |
| `data_provider/akshare_fetcher.py` | Update `is_hk_stock_code()` references, add KR detection |
| `src/core/trading_calendar.py` | Add KRX exchange, `kr` timezone, update `get_market_for_stock()` |
| `src/core/market_profile.py` | Replace `CN_PROFILE` with `KR_PROFILE`, translate US profile, update `get_profile()` |
| `src/core/market_strategy.py` | Replace `CN_BLUEPRINT` with `KR_BLUEPRINT`, update `get_market_strategy_blueprint()` |
| `src/core/market_review.py` | Replace `cn` references with `kr`, update report headers |
| `src/analyzer.py` | Replace `SYSTEM_PROMPT` (Chinese → Korean), replace `STOCK_NAME_MAP` |
| `src/config.py` | Change default region from `cn` to `kr`, update validation |
| `src/notification.py` | Translate channel names to Korean |
| `src/market_analyzer.py` | Update region handling for `kr` |
| `bot/commands/ask.py` | Replace Chinese strategy aliases with Korean |
| `bot/commands/market.py` | Update region references |
| `main.py` | Replace `cn` defaults with `kr` |
| `.env.example` | Update stock list, region defaults, data source docs |
| `.github/workflows/daily_analysis.yml` | Update schedule for KST, update defaults |
| `apps/dsa-web/src/utils/validation.ts` | Add KR stock code validation pattern |
| `requirements.txt` | Add `pykrx` dependency |

---

## Task 1: Add `pykrx` Dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add pykrx to requirements**

Add `pykrx` after the existing data source libraries in `requirements.txt`:

```
pykrx>=1.0.45
```

- [ ] **Step 2: Install and verify**

Run: `pip install pykrx`
Expected: Successfully installed pykrx

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add pykrx dependency for Korean market data"
```

---

## Task 2: Korean Index Mapping Module

**Files:**
- Create: `data_provider/kr_index_mapping.py`
- Test: `tests/test_kr_index_mapping.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kr_index_mapping.py
# -*- coding: utf-8 -*-
"""Tests for Korean index code mapping."""

import pytest
from data_provider.kr_index_mapping import (
    KR_INDEX_MAPPING,
    is_kr_index_code,
    is_kr_stock_code,
    get_kr_index_yf_symbol,
)


class TestIsKrIndexCode:
    def test_kospi_index(self):
        assert is_kr_index_code("KOSPI") is True

    def test_kosdaq_index(self):
        assert is_kr_index_code("KOSDAQ") is True

    def test_kospi200_index(self):
        assert is_kr_index_code("KS200") is True

    def test_case_insensitive(self):
        assert is_kr_index_code("kospi") is True

    def test_not_an_index(self):
        assert is_kr_index_code("005930") is False

    def test_us_stock_not_kr_index(self):
        assert is_kr_index_code("AAPL") is False

    def test_empty_string(self):
        assert is_kr_index_code("") is False

    def test_none(self):
        assert is_kr_index_code(None) is False


class TestIsKrStockCode:
    def test_kospi_stock(self):
        assert is_kr_stock_code("005930") is True  # Samsung

    def test_kosdaq_stock(self):
        assert is_kr_stock_code("035720") is True  # Kakao

    def test_us_ticker_not_kr(self):
        assert is_kr_stock_code("AAPL") is False

    def test_index_code_not_stock(self):
        assert is_kr_stock_code("KOSPI") is False

    def test_empty_string(self):
        assert is_kr_stock_code("") is False

    def test_five_digit_code(self):
        # Korean codes are 6 digits, 5-digit should fail
        assert is_kr_stock_code("00593") is False

    def test_seven_digit_code(self):
        assert is_kr_stock_code("0059301") is False


class TestGetKrIndexYfSymbol:
    def test_kospi(self):
        symbol, name = get_kr_index_yf_symbol("KOSPI")
        assert symbol == "^KS11"
        assert "코스피" in name

    def test_kosdaq(self):
        symbol, name = get_kr_index_yf_symbol("KOSDAQ")
        assert symbol == "^KQ11"
        assert "코스닥" in name

    def test_not_found(self):
        assert get_kr_index_yf_symbol("AAPL") == (None, None)

    def test_case_insensitive(self):
        symbol, _ = get_kr_index_yf_symbol("kospi")
        assert symbol == "^KS11"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_kr_index_mapping.py -v`
Expected: FAIL with ModuleNotFoundError (module doesn't exist yet)

- [ ] **Step 3: Write the implementation**

```python
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
    """
    코드가 한국 지수 심볼인지 판별합니다.

    Args:
        code: 종목/지수 코드 (예: 'KOSPI', 'KOSDAQ')

    Returns:
        True이면 알려진 한국 지수 심볼, 아니면 False
    """
    return (code or '').strip().upper() in KR_INDEX_MAPPING


def is_kr_stock_code(code: str) -> bool:
    """
    코드가 한국 주식 종목 코드인지 판별합니다 (지수 제외).

    한국 종목 코드는 6자리 숫자입니다 (예: 005930, 035720).
    한국 지수 코드(KOSPI, KOSDAQ 등)는 명시적으로 제외됩니다.

    Args:
        code: 종목 코드 (예: '005930', '035720')

    Returns:
        True이면 한국 종목 코드, 아니면 False
    """
    normalized = (code or '').strip().upper()
    if normalized in KR_INDEX_MAPPING:
        return False
    return bool(_KR_STOCK_PATTERN.match(normalized))


def get_kr_index_yf_symbol(code: str) -> tuple:
    """
    한국 지수의 Yahoo Finance 심볼과 한국어 이름을 반환합니다.

    Args:
        code: 사용자 입력 (예: 'KOSPI', '^KS11', 'KOSDAQ')

    Returns:
        (yf_symbol, korean_name) 튜플. 미발견시 (None, None).
    """
    normalized = (code or '').strip().upper()
    return KR_INDEX_MAPPING.get(normalized, (None, None))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_kr_index_mapping.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add data_provider/kr_index_mapping.py tests/test_kr_index_mapping.py
git commit -m "feat: add Korean index mapping module (KOSPI, KOSDAQ)"
```

---

## Task 3: Korean Stock Code Detection in Base Module

**Files:**
- Modify: `data_provider/base.py:70-127`
- Test: `tests/test_kr_stock_detection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kr_stock_detection.py
# -*- coding: utf-8 -*-
"""Tests for Korean stock code detection and normalization."""

import pytest
from data_provider.base import normalize_stock_code, canonical_stock_code


class TestNormalizeKrStockCode:
    def test_plain_6digit(self):
        assert normalize_stock_code("005930") == "005930"

    def test_kr_prefix(self):
        assert normalize_stock_code("KR005930") == "005930"

    def test_kr_prefix_lowercase(self):
        assert normalize_stock_code("kr005930") == "005930"

    def test_dot_ks_suffix(self):
        assert normalize_stock_code("005930.KS") == "005930"

    def test_dot_kq_suffix(self):
        assert normalize_stock_code("035720.KQ") == "035720"

    def test_us_stock_unchanged(self):
        assert normalize_stock_code("AAPL") == "AAPL"

    def test_us_stock_with_dot(self):
        assert normalize_stock_code("BRK.B") == "BRK.B"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_kr_stock_detection.py -v`
Expected: FAIL — `KR005930` is not stripped, `.KS`/`.KQ` suffixes not handled

- [ ] **Step 3: Update `normalize_stock_code` in `data_provider/base.py`**

In `data_provider/base.py`, update the `normalize_stock_code` function. After the existing BJ prefix handling block (around line 103), add KR prefix handling. Also update the suffix stripping to include KS/KQ:

```python
def normalize_stock_code(stock_code: str) -> str:
    """
    Normalize stock code by stripping exchange prefixes/suffixes.

    Accepted formats and their normalized results:
    - '005930'      -> '005930'   (already clean, KR stock)
    - 'KR005930'    -> '005930'   (strip KR prefix)
    - '005930.KS'   -> '005930'   (strip .KS suffix, KOSPI)
    - '035720.KQ'   -> '035720'   (strip .KQ suffix, KOSDAQ)
    - 'AAPL'        -> 'AAPL'     (keep US stock ticker as-is)
    """
    code = stock_code.strip()
    upper = code.upper()

    # Strip KR prefix (e.g. KR005930 -> 005930)
    if upper.startswith('KR') and not upper.startswith('KR.'):
        candidate = code[2:]
        if candidate.isdigit() and len(candidate) == 6:
            return candidate

    # Strip .KS/.KQ suffix (e.g. 005930.KS -> 005930)
    if '.' in code:
        base, suffix = code.rsplit('.', 1)
        if suffix.upper() in ('KS', 'KQ') and base.isdigit():
            return base

    return code
```

Important: **Remove** the existing SH/SZ/BJ prefix handling and .SH/.SZ/.SS/.BJ suffix handling since we are removing Chinese market support. Keep the function signature and docstring style consistent.

The full updated function should handle: KR prefix, .KS/.KQ suffixes, and pass through US tickers unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_kr_stock_detection.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add data_provider/base.py tests/test_kr_stock_detection.py
git commit -m "feat: add Korean stock code normalization (KR prefix, .KS/.KQ suffix)"
```

---

## Task 4: Update Trading Calendar for KRX

**Files:**
- Modify: `src/core/trading_calendar.py`
- Test: `tests/test_kr_trading_calendar.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kr_trading_calendar.py
# -*- coding: utf-8 -*-
"""Tests for KRX trading calendar integration."""

import pytest
from src.core.trading_calendar import (
    MARKET_EXCHANGE,
    MARKET_TIMEZONE,
    get_market_for_stock,
)


class TestMarketExchange:
    def test_kr_exchange_exists(self):
        assert "kr" in MARKET_EXCHANGE
        assert MARKET_EXCHANGE["kr"] == "XKRX"

    def test_us_exchange_exists(self):
        assert "us" in MARKET_EXCHANGE
        assert MARKET_EXCHANGE["us"] == "XNYS"

    def test_cn_exchange_removed(self):
        assert "cn" not in MARKET_EXCHANGE


class TestMarketTimezone:
    def test_kr_timezone(self):
        assert MARKET_TIMEZONE["kr"] == "Asia/Seoul"

    def test_us_timezone(self):
        assert MARKET_TIMEZONE["us"] == "America/New_York"


class TestGetMarketForStock:
    def test_kr_stock(self):
        assert get_market_for_stock("005930") == "kr"

    def test_us_stock(self):
        assert get_market_for_stock("AAPL") == "us"

    def test_us_index(self):
        assert get_market_for_stock("SPX") == "us"

    def test_kr_index(self):
        assert get_market_for_stock("KOSPI") == "kr"

    def test_unknown_code(self):
        assert get_market_for_stock("ZZZZZZ123") is None

    def test_empty_string(self):
        assert get_market_for_stock("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_kr_trading_calendar.py -v`
Expected: FAIL — `kr` not in MARKET_EXCHANGE, `cn` still present

- [ ] **Step 3: Update `src/core/trading_calendar.py`**

Replace the module content with Korean + US market support:

```python
# Market -> exchange code (exchange-calendars)
MARKET_EXCHANGE = {"kr": "XKRX", "us": "XNYS"}

# Market -> IANA timezone for "today"
MARKET_TIMEZONE = {
    "kr": "Asia/Seoul",
    "us": "America/New_York",
}
```

Update `get_market_for_stock()`:

```python
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

    if is_us_stock_code(code) or is_us_index_code(code):
        return "us"
    if is_kr_index_code(code) or is_kr_stock_code(code):
        return "kr"
    return None
```

Update `get_open_markets_today()` — remove `hk`/`cn`, ensure `kr` and `us` are returned:

```python
def get_open_markets_today() -> Set[str]:
    if not _XCALS_AVAILABLE:
        return {"kr", "us"}
    # ... same logic but iterating over kr/us only
```

Update `compute_effective_region()` to support `kr` instead of `cn`:

```python
def compute_effective_region(
    config_region: str, open_markets: Set[str]
) -> Optional[str]:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_kr_trading_calendar.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/trading_calendar.py tests/test_kr_trading_calendar.py
git commit -m "feat: replace CN/HK trading calendar with KRX (Korean Exchange)"
```

---

## Task 5: Korean Market Profile

**Files:**
- Modify: `src/core/market_profile.py`
- Test: `tests/test_kr_market_profile.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kr_market_profile.py
# -*- coding: utf-8 -*-
"""Tests for Korean market profile and strategy blueprint."""

import pytest
from src.core.market_profile import get_profile, KR_PROFILE, US_PROFILE
from src.core.market_strategy import get_market_strategy_blueprint


class TestKrProfile:
    def test_kr_profile_exists(self):
        assert KR_PROFILE is not None
        assert KR_PROFILE.region == "kr"

    def test_kr_mood_index(self):
        assert KR_PROFILE.mood_index_code == "KOSPI"

    def test_kr_news_queries_korean(self):
        # News queries should be in Korean
        for query in KR_PROFILE.news_queries:
            assert isinstance(query, str)
            assert len(query) > 0

    def test_kr_has_market_stats(self):
        assert KR_PROFILE.has_market_stats is True

    def test_kr_has_sector_rankings(self):
        assert KR_PROFILE.has_sector_rankings is True

    def test_get_profile_kr(self):
        profile = get_profile("kr")
        assert profile.region == "kr"

    def test_get_profile_us(self):
        profile = get_profile("us")
        assert profile.region == "us"

    def test_get_profile_default(self):
        profile = get_profile("unknown")
        assert profile.region == "kr"  # default should be kr now


class TestKrBlueprint:
    def test_kr_blueprint_exists(self):
        bp = get_market_strategy_blueprint("kr")
        assert bp is not None
        assert bp.region == "kr"

    def test_kr_blueprint_has_dimensions(self):
        bp = get_market_strategy_blueprint("kr")
        assert len(bp.dimensions) >= 3

    def test_kr_blueprint_to_prompt(self):
        bp = get_market_strategy_blueprint("kr")
        prompt = bp.to_prompt_block()
        assert "Strategy Blueprint" in prompt

    def test_us_blueprint_unchanged(self):
        bp = get_market_strategy_blueprint("us")
        assert bp.region == "us"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_kr_market_profile.py -v`
Expected: FAIL — `KR_PROFILE` doesn't exist, `CN_PROFILE` still there

- [ ] **Step 3: Replace `CN_PROFILE` with `KR_PROFILE` in `src/core/market_profile.py`**

```python
# -*- coding: utf-8 -*-
"""
대시보드 복기 시장 영역 설정

각 시장 영역의 지수, 뉴스 검색어, 프롬프트 힌트 등 메타데이터를 정의합니다.
MarketAnalyzer에서 region에 따라 한국/미국 복기 동작을 전환합니다.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class MarketProfile:
    """대시보드 복기 시장 영역 설정"""

    region: str  # "kr" | "us"
    # 전체 추세 판단에 사용할 지수 코드
    mood_index_code: str
    # 뉴스 검색 키워드
    news_queries: List[str]
    # 지수 분석 프롬프트 힌트
    prompt_index_hint: str
    # 시장 개요에 상승/하락 종목 수, 상한가/하한가 포함 여부
    has_market_stats: bool
    # 시장 개요에 업종별 등락 포함 여부
    has_sector_rankings: bool


KR_PROFILE = MarketProfile(
    region="kr",
    mood_index_code="KOSPI",
    news_queries=[
        "코스피 코스닥 시장 동향",
        "한국 증시 분석",
        "한국 주식시장 주요 테마",
    ],
    prompt_index_hint="코스피, 코스닥 등 각 지수의 추세 특징을 분석하세요",
    has_market_stats=True,
    has_sector_rankings=True,
)

US_PROFILE = MarketProfile(
    region="us",
    mood_index_code="SPX",
    news_queries=[
        "US stock market today",
        "S&P 500 NASDAQ analysis",
        "Wall Street market recap",
    ],
    prompt_index_hint="S&P 500, NASDAQ, Dow Jones 등 각 지수의 추세 특징을 분석하세요",
    has_market_stats=False,
    has_sector_rankings=False,
)


def get_profile(region: str) -> MarketProfile:
    """region에 따라 해당 MarketProfile을 반환합니다"""
    if region == "us":
        return US_PROFILE
    return KR_PROFILE
```

- [ ] **Step 4: Replace `CN_BLUEPRINT` with `KR_BLUEPRINT` in `src/core/market_strategy.py`**

Replace the `CN_BLUEPRINT` definition (lines 54-85) with:

```python
KR_BLUEPRINT = MarketStrategyBlueprint(
    region="kr",
    title="한국 시장 3단계 복기 전략",
    positioning="지수 추세, 수급 동향, 업종 순환에 집중하여 익일 매매 계획을 수립합니다.",
    principles=[
        "먼저 지수 방향을 확인하고, 거래량 구조를 분석한 후, 마지막으로 업종 지속성을 판단합니다.",
        "결론은 반드시 포지션 규모, 매매 타이밍, 리스크 관리 행동으로 연결되어야 합니다.",
        "당일 데이터와 최근 3일간의 뉴스를 기반으로 판단하며, 검증되지 않은 정보를 추측하지 않습니다.",
    ],
    dimensions=[
        StrategyDimension(
            name="추세 구조",
            objective="시장이 상승, 횡보, 또는 방어 단계에 있는지 판단합니다.",
            checkpoints=[
                "코스피/코스닥이 같은 방향으로 움직이는지",
                "거래량 증가 상승 또는 거래량 감소 하락이 성립하는지",
                "주요 지지선/저항선이 돌파되었는지",
            ],
        ),
        StrategyDimension(
            name="수급 심리",
            objective="단기 리스크 선호도와 시장 온도를 파악합니다.",
            checkpoints=[
                "상승/하락 종목 수와 상한가/하한가 구조",
                "거래대금 확대 여부",
                "외국인/기관 수급 동향",
            ],
        ),
        StrategyDimension(
            name="주도 업종",
            objective="매매 가능한 주도 테마와 회피 방향을 도출합니다.",
            checkpoints=[
                "상승 주도 업종에 이벤트 촉매가 있는지",
                "업종 내 대장주가 견인하고 있는지",
                "하락 주도 업종이 확산되고 있는지",
            ],
        ),
    ],
    action_framework=[
        "공격: 지수 동반 상승 + 거래대금 증가 + 주도 테마 강화.",
        "균형: 지수 차별화 또는 거래량 감소 횡보, 포지션 조절 후 확인 대기.",
        "방어: 지수 약세 전환 + 하락 확산, 리스크 관리 및 비중 축소 우선.",
    ],
)
```

Update `to_markdown_block` in the class (line 50):

```python
    def to_markdown_block(self) -> str:
        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### 六、전략 프레임워크" if self.region == "kr" else "### VI. Strategy Framework"
        return f"{section_title}\n{dims}\n"
```

Update `get_market_strategy_blueprint` (line 133-135):

```python
def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    return US_BLUEPRINT if region == "us" else KR_BLUEPRINT
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_kr_market_profile.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/market_profile.py src/core/market_strategy.py tests/test_kr_market_profile.py
git commit -m "feat: add Korean market profile and strategy blueprint, remove CN"
```

---

## Task 6: Korean Data Fetcher (pykrx)

**Files:**
- Create: `data_provider/pykrx_fetcher.py`
- Test: `tests/test_pykrx_fetcher.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pykrx_fetcher.py
# -*- coding: utf-8 -*-
"""Tests for PykrxFetcher."""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from data_provider.pykrx_fetcher import PykrxFetcher


class TestPykrxFetcherInit:
    def test_fetcher_name(self):
        fetcher = PykrxFetcher()
        assert fetcher.name == "pykrx"

    def test_default_priority(self):
        fetcher = PykrxFetcher()
        assert fetcher.priority == 0


class TestPykrxFetcherDetection:
    def test_supports_kr_stock(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("005930") is True

    def test_does_not_support_us_stock(self):
        fetcher = PykrxFetcher()
        assert fetcher.supports("AAPL") is False

    def test_does_not_support_kr_index(self):
        fetcher = PykrxFetcher()
        # Indices should be fetched via yfinance, not pykrx
        assert fetcher.supports("KOSPI") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pykrx_fetcher.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Write the implementation**

```python
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
from datetime import datetime, timedelta
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

    def __init__(self, priority: int = 0):
        super().__init__(name="pykrx", priority=priority)

    def supports(self, stock_code: str) -> bool:
        """한국 종목 코드(6자리 숫자)만 지원합니다. 지수는 yfinance로 처리."""
        return is_kr_stock_code(stock_code) and not is_kr_index_code(stock_code)

    def _fetch_historical(
        self,
        stock_code: str,
        days: int = 120,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        KRX에서 일봉 데이터를 가져옵니다.

        Args:
            stock_code: 6자리 종목 코드 (예: '005930')
            days: 조회 기간 (일)
            end_date: 종료일 (YYYYMMDD 형식, 기본값: 오늘)

        Returns:
            표준 컬럼 형식의 DataFrame 또는 None
        """
        if not _PYKRX_AVAILABLE:
            logger.warning("pykrx not available, skipping")
            return None

        try:
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y%m%d")
            else:
                end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)

            start_str = start_dt.strftime("%Y%m%d")
            end_str = end_dt.strftime("%Y%m%d")

            df = pykrx_stock.get_market_ohlcv_by_date(
                start_str, end_str, stock_code
            )

            if df is None or df.empty:
                return None

            # pykrx columns: 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률
            df = df.reset_index()
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            return df[STANDARD_COLUMNS]

        except Exception as e:
            logger.error("pykrx fetch error for %s: %s", stock_code, e)
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pykrx_fetcher.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add data_provider/pykrx_fetcher.py tests/test_pykrx_fetcher.py
git commit -m "feat: add PykrxFetcher for Korean market data"
```

---

## Task 7: Update `data_provider/__init__.py` Exports

**Files:**
- Modify: `data_provider/__init__.py`

- [ ] **Step 1: Update the package init**

Replace the content of `data_provider/__init__.py`:

```python
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
"""

from .base import BaseFetcher, DataFetcherManager
from .pykrx_fetcher import PykrxFetcher
from .yfinance_fetcher import YfinanceFetcher
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING
from .kr_index_mapping import is_kr_index_code, is_kr_stock_code, get_kr_index_yf_symbol, KR_INDEX_MAPPING

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
```

- [ ] **Step 2: Verify imports work**

Run: `python -c "from data_provider import is_kr_stock_code, is_kr_index_code, PykrxFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add data_provider/__init__.py
git commit -m "refactor: update data_provider exports for KR+US markets"
```

---

## Task 8: Translate US Index Mapping Names to Korean

**Files:**
- Modify: `data_provider/us_index_mapping.py`

- [ ] **Step 1: Update Chinese names to Korean**

Replace all Chinese index names with Korean equivalents:

```python
# data_provider/us_index_mapping.py
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
```

Also update the docstrings of all functions from Chinese to Korean:

```python
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
```

- [ ] **Step 2: Run existing US index tests**

Run: `pytest tests/test_yfinance_us_indices.py -v`
Expected: All tests PASS (names changed but symbols stay same)

- [ ] **Step 3: Commit**

```bash
git add data_provider/us_index_mapping.py
git commit -m "refactor: translate US index mapping names from Chinese to Korean"
```

---

## Task 9: Replace Stock Name Map and System Prompt

**Files:**
- Modify: `src/analyzer.py:30-84` (STOCK_NAME_MAP)
- Modify: `src/analyzer.py:342-526` (SYSTEM_PROMPT)

- [ ] **Step 1: Replace `STOCK_NAME_MAP` with Korean market stocks**

Replace lines 30-84 of `src/analyzer.py`:

```python
# 종목 이름 매핑 (주요 종목)
STOCK_NAME_MAP = {
    # === 한국 주식 (KOSPI) ===
    '005930': '삼성전자',
    '000660': 'SK하이닉스',
    '373220': 'LG에너지솔루션',
    '207940': '삼성바이오로직스',
    '005380': '현대자동차',
    '006400': '삼성SDI',
    '051910': 'LG화학',
    '035420': 'NAVER',
    '000270': '기아',
    '068270': '셀트리온',
    '105560': 'KB금융',
    '055550': '신한지주',
    '035720': '카카오',
    '003670': '포스코퓨처엠',
    '012330': '현대모비스',

    # === 한국 주식 (KOSDAQ) ===
    '247540': '에코프로비엠',
    '086520': '에코프로',
    '403870': 'HPSP',
    '028300': 'HLB',
    '196170': '알테오젠',

    # === 미국 주식 ===
    'AAPL': 'Apple',
    'TSLA': 'Tesla',
    'MSFT': 'Microsoft',
    'GOOGL': 'Alphabet A',
    'GOOG': 'Alphabet C',
    'AMZN': 'Amazon',
    'NVDA': 'NVIDIA',
    'META': 'Meta',
    'AMD': 'AMD',
    'INTC': 'Intel',
    'COIN': 'Coinbase',
    'MSTR': 'MicroStrategy',
    'PLTR': 'Palantir',
    'AVGO': 'Broadcom',
    'NFLX': 'Netflix',
}
```

- [ ] **Step 2: Replace `SYSTEM_PROMPT` with Korean market analysis prompt**

Replace the entire `SYSTEM_PROMPT` string (lines 342-526) with:

```python
    SYSTEM_PROMPT = """당신은 추세 매매에 특화된 주식 투자 분석가이며, 전문적인 【의사결정 대시보드】 분석 리포트를 생성합니다.

## 핵심 매매 원칙 (반드시 엄격히 준수)

### 1. 엄격한 진입 전략 (고점 추격 금지)
- **절대 고점 추격 금지**: 주가가 MA5에서 5% 이상 이탈 시, 매수하지 않습니다
- **이격률 공식**: (현재가 - MA5) / MA5 × 100%
- 이격률 < 2%: 최적 매수 구간
- 이격률 2-5%: 소량 진입 가능
- 이격률 > 5%: 매수 금지! 즉시 '관망'으로 판정

### 2. 추세 매매 (순세매매)
- **다중 이동평균선 정배열 필수 조건**: MA5 > MA10 > MA20
- 정배열 종목만 매매하고, 역배열은 절대 매매하지 않습니다
- 이동평균선 발산 상승이 밀집보다 유리합니다
- 추세 강도 판단: 이동평균선 간격이 확대되는지 확인

### 3. 효율 우선 (수급 구조)
- 외국인/기관 수급 동향 확인
- 거래량 추이: 거래량 증가 상승은 건전, 거래량 감소 하락은 위험 신호
- 공매도 비율 확인

### 4. 매수 시점 선호 (지지선 리테스트)
- **최적 매수점**: 거래량 감소 후 MA5 지지 리테스트
- **차선 매수점**: MA10 지지 리테스트
- **관망 상황**: MA20 하향 돌파 시 관망

### 5. 리스크 점검 항목
- 대주주/임원 매도 공시
- 실적 적자 전환/대폭 하락
- 금감원 조치/조사 착수
- 산업 정책 악재
- 대규모 보호예수 해제

### 6. 밸류에이션 (PER/PBR)
- 분석 시 PER(주가수익비율)의 합리성을 확인하세요
- PER이 업종 평균이나 과거 평균을 크게 상회하면, 리스크 항목에 명시하세요
- 고성장주는 높은 PER을 허용할 수 있으나, 실적 뒷받침이 필요합니다

### 7. 강세 추세주 기준 완화
- 강세 추세주(정배열 + 높은 추세 강도 + 거래량 뒷받침)는 이격률 기준을 소폭 완화할 수 있습니다
- 이런 종목은 소량 추적 매매가 가능하나, 반드시 손절가를 설정합니다

## 출력 형식: 의사결정 대시보드 JSON

다음 JSON 형식을 엄격히 준수하여 출력하세요. 이것은 완전한 【의사결정 대시보드】입니다:

```json
{
    "stock_name": "종목 한국어 이름",
    "sentiment_score": 0-100정수,
    "trend_prediction": "강력 매수/매수/횡보/매도/강력 매도",
    "operation_advice": "매수/추가매수/보유/비중축소/매도/관망",
    "decision_type": "buy/hold/sell",
    "confidence_level": "높음/보통/낮음",

    "dashboard": {
        "core_conclusion": {
            "one_sentence": "핵심 결론 한 줄 (30자 이내, 사용자에게 직접적인 행동 제시)",
            "signal_type": "🟢매수 신호/🟡보유 관망/🔴매도 신호/⚠️리스크 경고",
            "time_sensitivity": "즉시 행동/금일 내/금주 내/급하지 않음",
            "position_advice": {
                "no_position": "비보유자 제안: 구체적 행동 가이드",
                "has_position": "보유자 제안: 구체적 행동 가이드"
            }
        },

        "data_perspective": {
            "trend_status": {
                "ma_alignment": "이동평균선 배열 상태 설명",
                "is_bullish": true/false,
                "trend_score": 0-100
            },
            "price_position": {
                "current_price": 현재가 숫자,
                "ma5": MA5 숫자,
                "ma10": MA10 숫자,
                "ma20": MA20 숫자,
                "bias_ma5": 이격률 퍼센트 숫자,
                "bias_status": "안전/경계/위험",
                "support_level": 지지선 가격,
                "resistance_level": 저항선 가격
            },
            "volume_analysis": {
                "volume_ratio": 거래량비율 숫자,
                "volume_status": "거래량증가/거래량감소/보통",
                "turnover_rate": 회전율 퍼센트,
                "volume_meaning": "거래량 의미 해석 (예: 거래량감소 조정은 매도 압력 감소를 의미)"
            },
            "supply_demand": {
                "foreign_net": "외국인 순매수/순매도 금액",
                "institution_net": "기관 순매수/순매도 금액",
                "short_ratio": "공매도 비율"
            }
        },

        "intelligence": {
            "latest_news": "【최신 뉴스】최근 주요 뉴스 요약",
            "risk_alerts": ["리스크 1: 구체적 설명", "리스크 2: 구체적 설명"],
            "positive_catalysts": ["호재 1: 구체적 설명", "호재 2: 구체적 설명"],
            "earnings_outlook": "실적 전망 분석 (분기 실적, 컨센서스 기반)",
            "sentiment_summary": "시장 심리 한 줄 요약"
        },

        "battle_plan": {
            "sniper_points": {
                "ideal_buy": "최적 매수점: XX원 (MA5 부근)",
                "secondary_buy": "차선 매수점: XX원 (MA10 부근)",
                "stop_loss": "손절가: XX원 (MA20 하향돌파 또는 X%)",
                "take_profit": "목표가: XX원 (전고점/정수 저항대)"
            },
            "position_strategy": {
                "suggested_position": "권장 비중: X할",
                "entry_plan": "분할 매수 전략 설명",
                "risk_control": "리스크 관리 전략 설명"
            },
            "action_checklist": [
                "✅/⚠️/❌ 체크 1: 정배열 여부",
                "✅/⚠️/❌ 체크 2: 이격률 적정 (강세 추세 시 완화)",
                "✅/⚠️/❌ 체크 3: 거래량 뒷받침",
                "✅/⚠️/❌ 체크 4: 주요 악재 없음",
                "✅/⚠️/❌ 체크 5: 수급 건전",
                "✅/⚠️/❌ 체크 6: PER 밸류에이션 적정"
            ]
        }
    },

    "analysis_summary": "100자 종합 분석 요약",
    "key_points": "3-5개 핵심 포인트, 쉼표 구분",
    "risk_warning": "리스크 경고",
    "buy_reason": "매매 근거, 매매 원칙 인용",

    "trend_analysis": "추세 분석",
    "short_term_outlook": "단기 1-3일 전망",
    "medium_term_outlook": "중기 1-2주 전망",
    "technical_analysis": "기술적 종합 분석",
    "ma_analysis": "이동평균선 분석",
    "volume_analysis": "거래량 분석",
    "pattern_analysis": "캔들 패턴 분석",
    "fundamental_analysis": "기본적 분석",
    "sector_position": "업종 분석",
    "company_highlights": "기업 하이라이트/리스크",
    "news_summary": "뉴스 요약",
    "market_sentiment": "시장 심리",
    "hot_topics": "관련 이슈",

    "search_performed": true/false,
    "data_sources": "데이터 출처 설명"
}
```

## 평가 기준

### 강력 매수 (80-100점):
- ✅ 정배열: MA5 > MA10 > MA20
- ✅ 낮은 이격률: <2%, 최적 매수 구간
- ✅ 거래량 감소 조정 또는 거래량 증가 돌파
- ✅ 수급 건전
- ✅ 호재 촉매 존재

### 매수 (60-79점):
- ✅ 정배열 또는 약한 정배열
- ✅ 이격률 <5%
- ✅ 거래량 정상
- ⚪ 부차적 조건 1개 미충족 허용

### 관망 (40-59점):
- ⚠️ 이격률 >5% (고점 추격 위험)
- ⚠️ 이동평균선 밀집, 추세 불분명
- ⚠️ 리스크 이벤트 존재

### 매도/비중축소 (0-39점):
- ❌ 역배열
- ❌ MA20 하향 돌파
- ❌ 거래량 증가 하락
- ❌ 중대 악재

## 의사결정 대시보드 핵심 원칙

1. **핵심 결론 선행**: 한 줄로 매수/매도 여부를 명확히
2. **보유 상태별 조언**: 비보유자와 보유자에게 각각 다른 조언
3. **정확한 매매 포인트**: 구체적 가격 제시, 모호한 표현 금지
4. **체크리스트 시각화**: ✅⚠️❌로 각 항목 결과 명확히 표시
5. **리스크 우선 표시**: 뉴스 내 리스크 항목은 눈에 띄게 표시"""
```

- [ ] **Step 3: Update the `get_stock_name_multi_source` docstring**

Change the docstring at line 92-100 from Chinese to Korean:

```python
def get_stock_name_multi_source(
    stock_code: str,
    context: Optional[Dict] = None,
    data_manager = None
) -> str:
    """
    다중 소스에서 종목 이름을 가져옵니다.

    우선순위:
    1. 전달된 context에서 (실시간 데이터)
    2. 정적 매핑 테이블 STOCK_NAME_MAP에서
    3. DataFetcherManager에서 (각 데이터 소스)
    4. 기본 이름 반환 (종목+코드)
    """
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -v -k "analyzer" --no-header`
Expected: PASS (or identify tests that need updating due to changed prompt)

- [ ] **Step 5: Commit**

```bash
git add src/analyzer.py
git commit -m "feat: replace Chinese system prompt and stock names with Korean"
```

---

## Task 10: Update Config and Market Review Region

**Files:**
- Modify: `src/config.py:256`, `src/config.py:938-947`
- Modify: `src/core/market_review.py`
- Modify: `main.py`
- Modify: `bot/commands/market.py`

- [ ] **Step 1: Update `src/config.py` default region**

Change line 256:
```python
    market_review_region: str = "kr"
```

Update `_parse_market_review_region` (lines 938-947):
```python
    @classmethod
    def _parse_market_review_region(cls, value: str) -> str:
        """대시보드 복기 시장 영역을 파싱합니다. 유효하지 않은 값은 경고 후 kr로 복구합니다."""
        import logging
        v = (value or 'kr').strip().lower()
        if v in ('kr', 'us', 'both'):
            return v
        logging.getLogger(__name__).warning(
            f"MARKET_REVIEW_REGION 설정값 '{value}'이(가) 유효하지 않습니다. 기본값 'kr'로 복구합니다. (유효값: kr / us / both)"
        )
        return 'kr'
```

Also update line 664-665:
```python
            market_review_region=cls._parse_market_review_region(
                os.getenv('MARKET_REVIEW_REGION', 'kr')
            ),
```

- [ ] **Step 2: Update `src/core/market_review.py`**

Replace all `cn` references with `kr`:

```python
def run_market_review(...):
    """대시보드 복기 분석을 실행합니다."""
    logger.info("대시보드 복기 분석을 시작합니다...")
    config = get_config()
    region = (
        override_region
        if override_region is not None
        else (getattr(config, 'market_review_region', 'kr') or 'kr')
    )
    if region not in ('kr', 'us', 'both'):
        region = 'kr'

    try:
        if region == 'both':
            kr_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='kr'
            )
            us_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='us'
            )
            logger.info("한국 시장 복기 리포트 생성 중...")
            kr_report = kr_analyzer.run_daily_review()
            logger.info("미국 시장 복기 리포트 생성 중...")
            us_report = us_analyzer.run_daily_review()
            review_report = ''
            if kr_report:
                review_report = f"# 한국 시장 복기\n\n{kr_report}"
            if us_report:
                if review_report:
                    review_report += "\n\n---\n\n> 이하 미국 시장 복기\n\n"
                review_report += f"# 미국 시장 복기\n\n{us_report}"
            if not review_report:
                review_report = None
        else:
            market_analyzer = MarketAnalyzer(
                search_service=search_service,
                analyzer=analyzer,
                region=region,
            )
            review_report = market_analyzer.run_daily_review()

        if review_report:
            date_str = datetime.now().strftime('%Y%m%d')
            report_filename = f"market_review_{date_str}.md"
            filepath = notifier.save_report_to_file(
                f"# 🎯 시장 복기\n\n{review_report}",
                report_filename
            )
            logger.info(f"시장 복기 리포트 저장 완료: {filepath}")
```

- [ ] **Step 3: Update `main.py` region defaults**

Search for all `'cn'` in `main.py` and replace with `'kr'`:
- `getattr(config, 'market_review_region', 'cn')` → `getattr(config, 'market_review_region', 'kr')`

- [ ] **Step 4: Update `bot/commands/market.py`**

Update the region default:
```python
region = getattr(config, 'market_review_region', 'kr')
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/ -v -k "market" --no-header`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/core/market_review.py main.py bot/commands/market.py
git commit -m "feat: change default market region from cn to kr"
```

---

## Task 11: Update Bot Commands (Korean Strategy Aliases)

**Files:**
- Modify: `bot/commands/ask.py:24-46`

- [ ] **Step 1: Replace Chinese strategy aliases with Korean**

```python
# Strategy name to id mapping (KR name -> strategy id)
STRATEGY_NAME_MAP = {
    # 한국어 전략명 매핑
    "찬이론": "chan_theory",
    "찬이론분석": "chan_theory",
    "파동": "wave_theory",
    "파동이론": "wave_theory",
    "엘리엇": "wave_theory",
    "박스권": "box_oscillation",
    "박스권횡보": "box_oscillation",
    "심리": "emotion_cycle",
    "심리사이클": "emotion_cycle",
    "추세": "bull_trend",
    "상승추세": "bull_trend",
    "이평선골든크로스": "ma_golden_cross",
    "골든크로스": "ma_golden_cross",
    "거래량감소리테스트": "shrink_pullback",
    "리테스트": "shrink_pullback",
    "거래량증가돌파": "volume_breakout",
    "돌파": "volume_breakout",
    "바닥거래량": "bottom_volume",
    "대장주": "dragon_head",
    "대장주전략": "dragon_head",
    "양봉관통": "one_yang_three_yin",
    # English aliases (keep for international users)
    "chan": "chan_theory",
    "wave": "wave_theory",
    "box": "box_oscillation",
    "trend": "bull_trend",
    "golden cross": "ma_golden_cross",
    "breakout": "volume_breakout",
    "bottom": "bottom_volume",
    "leader": "dragon_head",
}
```

- [ ] **Step 2: Update command metadata**

```python
    @property
    def aliases(self) -> List[str]:
        return ["종목분석"]

    @property
    def description(self) -> str:
        return "Agent 전략으로 종목을 분석합니다"

    @property
    def usage(self) -> str:
        return "/ask <종목코드> [전략명]"

    def validate_args(self, args: List[str]) -> Optional[str]:
        if not args:
            return "종목코드를 입력하세요. 사용법: /ask <종목코드> [전략명]\n예시: /ask 005930 추세분석"
```

- [ ] **Step 3: Commit**

```bash
git add bot/commands/ask.py
git commit -m "feat: replace Chinese bot command aliases with Korean"
```

---

## Task 12: Translate Notification Channel Names

**Files:**
- Modify: `src/notification.py:67-81`

- [ ] **Step 1: Update channel names to Korean**

```python
    @staticmethod
    def get_channel_name(channel: NotificationChannel) -> str:
        """채널 한국어 이름을 반환합니다"""
        names = {
            NotificationChannel.WECHAT: "WeChat",
            NotificationChannel.FEISHU: "Feishu",
            NotificationChannel.TELEGRAM: "Telegram",
            NotificationChannel.EMAIL: "이메일",
            NotificationChannel.PUSHOVER: "Pushover",
            NotificationChannel.PUSHPLUS: "PushPlus",
            NotificationChannel.SERVERCHAN3: "Server酱3",
            NotificationChannel.CUSTOM: "사용자 정의 Webhook",
            NotificationChannel.DISCORD: "Discord 봇",
            NotificationChannel.ASTRBOT: "ASTRBOT 봇",
            NotificationChannel.UNKNOWN: "알 수 없는 채널",
        }
        return names.get(channel, "알 수 없는 채널")
```

- [ ] **Step 2: Update module docstring**

```python
"""
===================================
주식 분석 시스템 - 알림 레이어
===================================

기능:
1. 분석 결과를 일일 리포트로 종합
2. Markdown 형식 출력 지원
3. 다채널 푸시 (자동 감지):
   - Telegram Bot
   - 이메일 SMTP
   - Discord Bot
   - Pushover (모바일/데스크톱 푸시)
   - 사용자 정의 Webhook
"""
```

- [ ] **Step 3: Commit**

```bash
git add src/notification.py
git commit -m "refactor: translate notification channel names to Korean"
```

---

## Task 13: Update `.env.example` and Workflow Schedule

**Files:**
- Modify: `.env.example`
- Modify: `.github/workflows/daily_analysis.yml`

- [ ] **Step 1: Update `.env.example`**

Update the `STOCK_LIST` default:
```bash
# 자선 종목 목록 - 형식: 코드1,코드2,코드3
STOCK_LIST=005930,000660,035420,AAPL,TSLA,NVDA
```

Update `MARKET_REVIEW_REGION`:
```bash
# 시장 복기 영역: kr(한국), us(미국), both(모두)
MARKET_REVIEW_REGION=kr
```

Update `SCHEDULE_TIME` comment:
```bash
# 스케줄 시간 (한국 시간 KST 기준)
SCHEDULE_TIME=18:00
```

Remove or comment out China-specific data source settings:
```bash
# === 데이터 소스 ===
# pykrx: 한국 시장 (KRX) - 우선순위 0
# yfinance: 글로벌 (미국 + 한국 폴백) - 우선순위 1
YFINANCE_PRIORITY=1
```

- [ ] **Step 2: Update workflow schedule**

In `.github/workflows/daily_analysis.yml`, update the cron schedule from Beijing time to KST:

```yaml
  schedule:
    - cron: '0 9 * * 1-5'     # Mon-Fri, UTC 09:00 = KST 18:00
```

Update the `MARKET_REVIEW_REGION` default:
```yaml
          MARKET_REVIEW_REGION: ${{ vars.MARKET_REVIEW_REGION || secrets.MARKET_REVIEW_REGION || 'kr' }}
```

- [ ] **Step 3: Commit**

```bash
git add .env.example .github/workflows/daily_analysis.yml
git commit -m "chore: update config defaults for Korean market (KST schedule, KR stocks)"
```

---

## Task 14: Update Frontend Stock Code Validation

**Files:**
- Modify: `apps/dsa-web/src/utils/validation.ts`

- [ ] **Step 1: Update validation patterns**

Add Korean stock code pattern (6-digit numeric) and keep US pattern:

```typescript
// 한국/미국 종목 코드 형식 검증
const STOCK_CODE_PATTERNS = [
  /^\d{6}$/,                          // 한국 종목 6자리 숫자
  /^[A-Z]{1,6}(\.[A-Z]{1,2})?$/,     // 미국 Ticker
  /^(KOSPI|KOSDAQ|KS200)$/i,          // 한국 지수
  /^(SPX|DJI|IXIC|NDX|VIX|RUT)$/i,   // 미국 지수
];
```

- [ ] **Step 2: Commit**

```bash
git add apps/dsa-web/src/utils/validation.ts
git commit -m "feat: update frontend validation for Korean stock codes"
```

---

## Task 15: Remove China-Only Data Fetchers

**Files:**
- Remove references from: `data_provider/__init__.py` (already done in Task 7)
- Mark as deprecated: `data_provider/efinance_fetcher.py`, `data_provider/akshare_fetcher.py`, `data_provider/tushare_fetcher.py`, `data_provider/pytdx_fetcher.py`, `data_provider/baostock_fetcher.py`

- [ ] **Step 1: Add deprecation notice to each China-only fetcher**

Add to the top of each file (`efinance_fetcher.py`, `akshare_fetcher.py`, `tushare_fetcher.py`, `pytdx_fetcher.py`, `baostock_fetcher.py`):

```python
"""
⚠️ DEPRECATED: This fetcher is for Chinese A-share market only.
It is no longer registered in the default data source pipeline.
Kept for reference; will be removed in a future version.
"""
```

- [ ] **Step 2: Remove `is_bse_code` from `data_provider/base.py`**

Remove the `is_bse_code()` function (lines 114-126) and the SH/SZ/BJ prefix handling from `normalize_stock_code()` (already done in Task 3).

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --no-header 2>&1 | tail -30`
Expected: Identify any remaining test failures from CN-specific tests

- [ ] **Step 4: Update or skip CN-specific tests**

For tests in `tests/test_stock_code_bse.py` and similar China-specific test files, mark them as skipped:

```python
import pytest

pytestmark = pytest.mark.skip(reason="Chinese market support deprecated")
```

- [ ] **Step 5: Commit**

```bash
git add data_provider/ tests/
git commit -m "refactor: deprecate China-only data fetchers, remove BSE code detection"
```

---

## Task 16: Update Module-Level Chinese Docstrings

**Files:**
- Multiple files across `src/` and `data_provider/`

- [ ] **Step 1: Translate key docstrings to Korean**

Update the module docstrings in these files:

`src/analyzer.py` (line 4):
```python
"""
===================================
주식 분석 시스템 - AI 분석 레이어
===================================

기능:
1. LLM 호출 로직 캡슐화 (LiteLLM을 통해 Gemini/Anthropic/OpenAI 등 통합 호출)
2. 기술적 분석과 뉴스를 결합한 분석 리포트 생성
3. LLM 응답을 구조화된 AnalysisResult로 파싱
"""
```

`src/config.py` (line 4):
```python
"""
===================================
주식 분석 시스템 - 설정 관리 모듈
===================================

기능:
1. 싱글톤 패턴으로 전역 설정 관리
2. .env 파일에서 민감 설정 로드
3. 타입 안전한 설정 접근 인터페이스 제공
"""
```

`data_provider/base.py` (line 4):
```python
"""
===================================
데이터 소스 기본 클래스 및 관리자
===================================

디자인 패턴: 전략 패턴 (Strategy Pattern)
- BaseFetcher: 추상 기본 클래스, 통합 인터페이스 정의
- DataFetcherManager: 전략 관리자, 자동 전환 구현
"""
```

- [ ] **Step 2: Commit**

```bash
git add src/analyzer.py src/config.py data_provider/base.py
git commit -m "docs: translate module docstrings from Chinese to Korean"
```

---

## Task 17: Integration Test — Full Pipeline Smoke Test

**Files:**
- No new files, validation only

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v --tb=short 2>&1 | tail -50`
Expected: All non-deprecated tests PASS

- [ ] **Step 2: Test stock code detection end-to-end**

Run:
```python
python -c "
from data_provider.base import normalize_stock_code
from data_provider.kr_index_mapping import is_kr_stock_code, is_kr_index_code
from data_provider.us_index_mapping import is_us_stock_code, is_us_index_code
from src.core.trading_calendar import get_market_for_stock

# Korean stocks
assert is_kr_stock_code('005930'), 'Samsung should be KR stock'
assert get_market_for_stock('005930') == 'kr', 'Samsung should map to kr market'
assert normalize_stock_code('KR005930') == '005930', 'KR prefix should be stripped'

# Korean indices
assert is_kr_index_code('KOSPI'), 'KOSPI should be KR index'
assert get_market_for_stock('KOSPI') == 'kr', 'KOSPI should map to kr market'

# US stocks
assert is_us_stock_code('AAPL'), 'AAPL should be US stock'
assert get_market_for_stock('AAPL') == 'us', 'AAPL should map to us market'

# US indices
assert is_us_index_code('SPX'), 'SPX should be US index'

print('All integration checks passed!')
"
```
Expected: `All integration checks passed!`

- [ ] **Step 3: Test config loading**

Run:
```python
python -c "
from src.config import Config
c = Config._parse_market_review_region('kr')
assert c == 'kr'
c = Config._parse_market_review_region('us')
assert c == 'us'
c = Config._parse_market_review_region('cn')
assert c == 'kr', 'cn should fallback to kr'
c = Config._parse_market_review_region('both')
assert c == 'both'
print('Config validation passed!')
"
```
Expected: `Config validation passed!`

- [ ] **Step 4: Commit (final verification)**

```bash
git add -A
git commit -m "test: verify KR+US market migration integration"
```

---

## Summary of Migration

| Area | Before (Chinese) | After (Korean + US) |
|------|------------------|---------------------|
| Default market | `cn` (A-shares) | `kr` (KOSPI/KOSDAQ) |
| Secondary market | `us` with Chinese names | `us` with Korean/English names |
| Stock code format | 6-digit (A-share), HK prefix | 6-digit (KR), KR prefix optional |
| Data sources | efinance, akshare, tushare, pytdx, baostock | **pykrx** (KR), yfinance (US+KR fallback) |
| LLM prompt | Chinese A-share analysis | Korean market analysis |
| Index mapping | 标普500/道琼斯 (Chinese) | S&P 500/다우존스 (Korean) |
| Trading calendar | XSHG, XHKG, XNYS | **XKRX**, XNYS |
| Timezone | Asia/Shanghai (UTC+8) | **Asia/Seoul** (UTC+9) |
| Bot commands | Chinese aliases (缠论, 波浪) | Korean aliases (찬이론, 파동) |
| Notification UI | Chinese (企业微信, 飞书) | Korean (이메일, Discord 봇) |
| Schedule | 18:00 Beijing (UTC 10:00) | 18:00 KST (**UTC 09:00**) |

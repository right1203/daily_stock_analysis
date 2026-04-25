# -*- coding: utf-8 -*-
"""
===================================
Market recap analyzer
===================================

Responsibilities:
1. Fetch major market index data.
2. Search market news for recap context.
3. Generate a daily market recap report with an LLM.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd

from src.config import get_config
from src.search_service import SearchService
from src.core.market_profile import get_profile, MarketProfile
from src.core.market_strategy import get_market_strategy_blueprint
from data_provider.base import DataFetcherManager

logger = logging.getLogger(__name__)


@dataclass
class MarketIndex:
    """Major market index quote."""

    code: str
    name: str
    current: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    prev_close: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    amplitude: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current': self.current,
            'change': self.change,
            'change_pct': self.change_pct,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'amplitude': self.amplitude,
        }


@dataclass
class MarketOverview:
    """Market overview data."""

    date: str
    indices: List[MarketIndex] = field(default_factory=list)
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    total_amount: float = 0.0
    
    top_sectors: List[Dict] = field(default_factory=list)
    bottom_sectors: List[Dict] = field(default_factory=list)


class MarketAnalyzer:
    """
    Market recap analyzer.
    
    Responsibilities:
    1. Fetch major market index quotes
    2. Fetch market breadth statistics where available
    3. Fetch sector rankings where available
    4. Search market news
    5. Generate a market recap report
    """
    
    def __init__(
        self,
        search_service: Optional[SearchService] = None,
        analyzer=None,
        region: str = "kr",
    ):
        """
        Initialize the market analyzer.

        Args:
            search_service: Search service instance.
            analyzer: Analyzer instance used for LLM calls.
            region: Market region, kr for Korean stocks or us for US stocks.
        """
        self.config = get_config()
        self.search_service = search_service
        self.analyzer = analyzer
        self.data_manager = DataFetcherManager()
        self.region = region if region in ("kr", "us") else "kr"
        self.profile: MarketProfile = get_profile(self.region)
        self.strategy = get_market_strategy_blueprint(self.region)

    def get_market_overview(self) -> MarketOverview:
        """Fetch market overview data."""
        today = datetime.now().strftime('%Y-%m-%d')
        overview = MarketOverview(date=today)
        
        # 1. Fetch major index quotes for the selected KR/US region.
        overview.indices = self._get_main_indices()

        # 2. Fetch breadth statistics where the region supports them.
        if self.profile.has_market_stats:
            self._get_market_statistics(overview)

        # 3. Fetch sector rankings where the region supports them.
        if self.profile.has_sector_rankings:
            self._get_sector_rankings(overview)
        
        return overview

    
    def _get_main_indices(self) -> List[MarketIndex]:
        """Fetch real-time major index quotes."""
        indices = []

        try:
            logger.info("[Market] Fetching real-time major index quotes...")

            # Use DataFetcherManager to fetch index quotes for the active region.
            data_list = self.data_manager.get_main_indices(region=self.region)

            if data_list:
                for item in data_list:
                    index = MarketIndex(
                        code=item['code'],
                        name=item['name'],
                        current=item['current'],
                        change=item['change'],
                        change_pct=item['change_pct'],
                        open=item['open'],
                        high=item['high'],
                        low=item['low'],
                        prev_close=item['prev_close'],
                        volume=item['volume'],
                        amount=item['amount'],
                        amplitude=item['amplitude']
                    )
                    indices.append(index)

            if not indices:
                logger.warning("[Market] All quote data sources failed; analysis will rely on news search")
            else:
                logger.info(f"[Market] Fetched {len(indices)} index quote(s)")

        except Exception as e:
            logger.error(f"[Market] Failed to fetch index quotes: {e}")

        return indices

    def _get_market_statistics(self, overview: MarketOverview):
        """Fetch market breadth statistics."""
        try:
            logger.info("[Market] Fetching market breadth statistics...")

            stats = self.data_manager.get_market_stats()

            if stats:
                overview.up_count = stats.get('up_count', 0)
                overview.down_count = stats.get('down_count', 0)
                overview.flat_count = stats.get('flat_count', 0)
                overview.limit_up_count = stats.get('limit_up_count', 0)
                overview.limit_down_count = stats.get('limit_down_count', 0)
                overview.total_amount = stats.get('total_amount', 0.0)

                logger.info(
                    f"[Market] Up:{overview.up_count} Down:{overview.down_count} Flat:{overview.flat_count} "
                    f"Limit up:{overview.limit_up_count} Limit down:{overview.limit_down_count} "
                    f"Turnover:{overview.total_amount:.0f}"
                )

        except Exception as e:
            logger.error(f"[Market] Failed to fetch market breadth statistics: {e}")

    def _get_sector_rankings(self, overview: MarketOverview):
        """Fetch sector performance rankings."""
        try:
            logger.info("[Market] Fetching sector rankings...")

            top_sectors, bottom_sectors = self.data_manager.get_sector_rankings(5)

            if top_sectors or bottom_sectors:
                overview.top_sectors = top_sectors
                overview.bottom_sectors = bottom_sectors

                logger.info(f"[Market] Leading sectors: {[s['name'] for s in overview.top_sectors]}")
                logger.info(f"[Market] Lagging sectors: {[s['name'] for s in overview.bottom_sectors]}")

        except Exception as e:
            logger.error(f"[Market] Failed to fetch sector rankings: {e}")

    def search_market_news(self) -> List[Dict]:
        """
        Search market news.
        
        Returns:
            News item list.
        """
        if not self.search_service:
            logger.warning("[Market] Search service is not configured; skipping news search")
            return []
        
        all_news = []
        today = datetime.now()
        date_str = today.strftime('%Y-%m-%d')

        # Use region-specific market news queries.
        search_queries = self.profile.news_queries
        
        try:
            logger.info("[Market] Starting market news search...")
            
            # Keep market context explicit so KR and US searches use the correct provider route.
            market_code = "KOSPI" if self.region == "kr" else "SPX"
            market_name = "Korean market" if self.region == "kr" else "US market"
            for query in search_queries:
                response = self.search_service.search_stock_news(
                    stock_code=market_code,
                    stock_name=market_name,
                    max_results=3,
                    focus_keywords=query.split()
                )
                if response and response.results:
                    all_news.extend(response.results)
                    logger.info(f"[Market] Search '{query}' returned {len(response.results)} result(s)")

            logger.info(f"[Market] Fetched {len(all_news)} market news item(s)")

        except Exception as e:
            logger.error(f"[Market] Failed to search market news: {e}")
        
        return all_news
    
    def generate_market_review(self, overview: MarketOverview, news: List) -> str:
        """
        Generate the market recap report with an LLM.
        
        Args:
            overview: Market overview data.
            news: Market news items.
            
        Returns:
            Market recap report text.
        """
        if not self.analyzer or not self.analyzer.is_available():
            logger.warning("[Market] AI analyzer is unavailable; generating a template report")
            return self._generate_template_review(overview, news)
        
        # Build prompt.
        prompt = self._build_review_prompt(overview, news)
        
        logger.info("[Market] Calling LLM to generate market recap...")
        # Use the public generate_text() entry point — never access private analyzer attributes.
        review = self.analyzer.generate_text(prompt, max_tokens=2048, temperature=0.7)

        if review:
            logger.info("[Market] Market recap generated successfully, length=%d chars", len(review))
            # Inject structured data tables into LLM prose sections.
            return self._inject_data_into_review(review, overview)
        else:
            logger.warning("[Market] LLM returned an empty response; using template report")
            return self._generate_template_review(overview, news)
    
    def _inject_data_into_review(self, review: str, overview: MarketOverview) -> str:
        """Inject structured data tables into the corresponding LLM prose sections."""
        import re

        # Build data blocks
        stats_block = self._build_stats_block(overview)
        indices_block = self._build_indices_block(overview)
        sector_block = self._build_sector_block(overview)

        # Inject market stats after the market summary section.
        if stats_block:
            review = self._insert_after_section(review, r'###\s*1\.\s*(시장 요약|Market Summary)', stats_block)

        # Inject the index table after the index commentary section.
        if indices_block:
            review = self._insert_after_section(
                review,
                r'###\s*2\.\s*(지수 코멘트|Index Commentary)',
                indices_block,
            )

        # Inject sector rankings after the sector/theme section.
        if sector_block:
            review = self._insert_after_section(
                review,
                r'###\s*4\.\s*(섹터/테마 해석|Sector/Theme Highlights)',
                sector_block,
            )

        return review

    @staticmethod
    def _insert_after_section(text: str, heading_pattern: str, block: str) -> str:
        """Insert a data block at the end of a markdown section (before the next ### heading)."""
        import re
        # Find the heading
        match = re.search(heading_pattern, text)
        if not match:
            return text
        start = match.end()
        # Find the next ### heading after this one
        next_heading = re.search(r'\n###\s', text[start:])
        if next_heading:
            insert_pos = start + next_heading.start()
        else:
            # No next heading — append at end
            insert_pos = len(text)
        # Insert the block before the next heading, with spacing
        return text[:insert_pos].rstrip() + '\n\n' + block + '\n\n' + text[insert_pos:].lstrip('\n')

    def _build_stats_block(self, overview: MarketOverview) -> str:
        """Build market statistics block."""
        has_stats = overview.up_count or overview.down_count or overview.total_amount
        if not has_stats:
            return ""
        lines = [
            f"> 📈 상승 **{overview.up_count}**개 / 하락 **{overview.down_count}**개 / "
            f"보합 **{overview.flat_count}**개 | "
            f"상한가 **{overview.limit_up_count}** / 하한가 **{overview.limit_down_count}** | "
            f"거래대금 **{overview.total_amount:.0f}**억"
        ]
        return "\n".join(lines)

    def _build_indices_block(self, overview: MarketOverview) -> str:
        """Build an index quote table without amplitude."""
        if not overview.indices:
            return ""
        lines = [
            "| 지수 | 현재가 | 등락률 | 거래대금(억) |",
            "|------|------|--------|-----------|"]
        for idx in overview.indices:
            arrow = "🔴" if idx.change_pct < 0 else "🟢" if idx.change_pct > 0 else "⚪"
            amount_raw = idx.amount or 0.0
            if amount_raw == 0.0:
                # Yahoo Finance does not provide turnover amount; show N/A to avoid confusion.
                amount_str = "N/A"
            elif amount_raw > 1e6:
                amount_str = f"{amount_raw / 1e8:.0f}"
            else:
                amount_str = f"{amount_raw:.0f}"
            lines.append(f"| {idx.name} | {idx.current:.2f} | {arrow} {idx.change_pct:+.2f}% | {amount_str} |")
        return "\n".join(lines)

    def _build_sector_block(self, overview: MarketOverview) -> str:
        """Build sector ranking block."""
        if not overview.top_sectors and not overview.bottom_sectors:
            return ""
        lines = []
        if overview.top_sectors:
            top = " | ".join(
                [f"**{s['name']}**({s['change_pct']:+.2f}%)" for s in overview.top_sectors[:5]]
            )
            lines.append(f"> 🔥 강세: {top}")
        if overview.bottom_sectors:
            bot = " | ".join(
                [f"**{s['name']}**({s['change_pct']:+.2f}%)" for s in overview.bottom_sectors[:5]]
            )
            lines.append(f"> 💧 약세: {bot}")
        return "\n".join(lines)

    def _build_review_prompt(self, overview: MarketOverview, news: List) -> str:
        """Build the market recap prompt."""
        # Major index information in a compact format.
        indices_text = ""
        for idx in overview.indices:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            indices_text += f"- {idx.name}: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)\n"
        
        # Sector information.
        top_sectors_text = ", ".join([f"{s['name']}({s['change_pct']:+.2f}%)" for s in overview.top_sectors[:3]])
        bottom_sectors_text = ", ".join([f"{s['name']}({s['change_pct']:+.2f}%)" for s in overview.bottom_sectors[:3]])
        
        # News information; supports SearchResult objects and dicts.
        news_text = ""
        for i, n in enumerate(news[:6], 1):
            if hasattr(n, 'title'):
                title = n.title[:50] if n.title else ''
                snippet = n.snippet[:100] if n.snippet else ''
            else:
                title = n.get('title', '')[:50]
                snippet = n.get('snippet', '')[:100]
            news_text += f"{i}. {title}\n   {snippet}\n"
        
        # Build region-specific overview and sector blocks.
        stats_block = ""
        sector_block = ""
        if self.region == "us":
            if self.profile.has_market_stats:
                stats_block = f"""## 시장 개요
- 상승: {overview.up_count}개 | 하락: {overview.down_count}개 | 보합: {overview.flat_count}개
- 상한가: {overview.limit_up_count}개 | 하한가: {overview.limit_down_count}개
- 총 거래량: {overview.total_amount:.0f}"""
            else:
                stats_block = "## 시장 개요\n(미국 시장은 등락 종목 수 통계를 제공하지 않습니다.)"

            if self.profile.has_sector_rankings:
                sector_block = f"""## 업종 동향
강세: {top_sectors_text if top_sectors_text else "데이터 없음"}
약세: {bottom_sectors_text if bottom_sectors_text else "데이터 없음"}"""
            else:
                sector_block = "## 업종 동향\n(미국 업종 등락 데이터를 제공하지 않습니다.)"
        else:
            if self.profile.has_market_stats:
                stats_block = f"""## 시장 개요
- 상승: {overview.up_count}개 | 하락: {overview.down_count}개 | 보합: {overview.flat_count}개
- 상한가: {overview.limit_up_count}개 | 하한가: {overview.limit_down_count}개
- 거래대금: {overview.total_amount:.0f}억원"""
            else:
                stats_block = (
                    "## 시장 개요\n"
                    "(해당 시장은 등락 종목 수 통계를 제공하지 않습니다.)"
                )

            if self.profile.has_sector_rankings:
                sector_block = f"""## 업종 동향
강세: {top_sectors_text if top_sectors_text else "데이터 없음"}
약세: {bottom_sectors_text if bottom_sectors_text else "데이터 없음"}"""
            else:
                sector_block = (
                    "## 업종 동향\n"
                    "(해당 시장은 업종 등락 데이터를 제공하지 않습니다.)"
                )

        data_no_indices_hint = (
            "주의: 시세 데이터 조회에 실패했습니다. "
            "[시장 뉴스]를 중심으로 정성적으로 분석하고 "
            "지수 수치를 임의로 만들지 마세요."
            if not indices_text
            else ""
        )
        indices_placeholder = indices_text if indices_text else (
            "지수 데이터 없음(API 오류)" if self.region == "us" else "지수 데이터 없음(API 오류)"
        )
        news_placeholder = news_text if news_text else (
            "관련 뉴스 없음" if self.region == "us" else "관련 뉴스 없음"
        )

        # Use Korean prompts for US market recaps.
        if self.region == "us":
            data_no_indices_hint_us = (
                "주의: 시세 데이터 조회에 실패했습니다. "
                "[시장 뉴스]를 중심으로 정성적으로 분석하고 "
                "지수 수치를 임의로 만들지 마세요."
                if not indices_text
                else ""
            )
            us_prompt_intro = (
                "당신은 전문 미국 시장 애널리스트입니다.\n"
                "아래 데이터를 바탕으로 간결한 미국 시장 데일리 리캡을 작성하세요."
            )
            return f"""{us_prompt_intro}

[중요] 출력 요구사항:
- 반드시 순수 Markdown 텍스트로만 출력하세요.
- JSON 형식은 금지합니다.
- 코드 블록은 금지합니다.
- emoji는 제목에서만 적게 사용하세요(제목당 최대 1개).

---

# 오늘의 시장 데이터

## 날짜
{overview.date}

## 주요 지수
{indices_placeholder}

{stats_block}

{sector_block}

## 시장 뉴스
{news_placeholder}

{data_no_indices_hint_us}

{self.strategy.to_prompt_block()}

---

# 출력 형식 템플릿(아래 구조를 엄격히 따르세요)

## {overview.date} 미국 시장 리캡

### 1. 시장 요약
(2-3문장으로 시장 전반, 주요 지수 등락, 거래 흐름을 요약)

### 2. 지수 코멘트
(S&P 500, Nasdaq, Dow 등 주요 지수 움직임을 분석)

### 3. 수급 흐름
(거래량과 자금 흐름의 의미를 해석)

### 4. 섹터/테마 해석
(강세 및 약세 섹터의 배경과 동인을 분석)

### 5. 향후 전망
(가격 흐름과 뉴스를 바탕으로 단기 시장을 전망)

### 6. 리스크 점검
(주의해야 할 핵심 리스크 요인)

### 7. 전략 계획
(리스크온/중립/리스크오프 중 하나의 결론, 포지션 규모 가이드, 무효화 조건 1개를 제시하세요.)

---

리캡 본문만 바로 출력하고 추가 설명은 쓰지 마세요.
"""

        # Use a Korean prompt for KR market recaps.
        return f"""당신은 전문 한국 시장 애널리스트입니다.
아래 데이터를 바탕으로 간결한 한국 시장 데일리 리캡을 작성하세요.

[중요] 출력 요구사항:
- 반드시 순수 Markdown 텍스트로만 출력하세요.
- JSON 형식은 금지합니다.
- 코드 블록은 금지합니다.
- emoji는 제목에서만 적게 사용하세요(제목당 최대 1개).

---

# 오늘의 시장 데이터

## 날짜
{overview.date}

## 주요 지수
{indices_placeholder}

{stats_block}

{sector_block}

## 시장 뉴스
{news_placeholder}

{data_no_indices_hint}

{self.strategy.to_prompt_block()}

---

# 출력 형식 템플릿(아래 구조를 엄격히 따르세요)

## {overview.date} 한국 시장 리캡

### 1. 시장 요약
(2-3문장으로 오늘 시장 전반, 주요 지수 등락, 거래 흐름을 요약)

### 2. 지수 코멘트
({self.profile.prompt_index_hint})

### 3. 수급 흐름
(거래대금과 수급 흐름의 의미를 해석)

### 4. 섹터/테마 해석
(강세 및 약세 업종의 배경과 동인을 분석)

### 5. 향후 전망
(현재 흐름과 뉴스를 바탕으로 다음 거래일 시장을 전망)

### 6. 리스크 점검
(주의해야 할 리스크 요인)

### 7. 전략 계획
(공격/중립/방어 중 하나의 결론, 대응 포지션 가이드, 무효화 조건 1개를 제시하세요.
마지막에 "본 내용은 참고용이며 투자 조언이 아닙니다."를 덧붙이세요.)

---

리캡 본문만 바로 출력하고 추가 설명은 쓰지 마세요.
"""
    
    def _generate_template_review(self, overview: MarketOverview, news: List) -> str:
        """Generate a template report when no LLM is available."""
        mood_code = self.profile.mood_index_code
        # Match direct index codes and normalized provider symbols that end with the mood code.
        mood_index = next(
            (
                idx
                for idx in overview.indices
                if idx.code == mood_code or idx.code.endswith(mood_code)
            ),
            None,
        )
        if mood_index:
            if mood_index.change_pct > 1:
                market_mood = "강한 상승"
            elif mood_index.change_pct > 0:
                market_mood = "소폭 상승"
            elif mood_index.change_pct > -1:
                market_mood = "소폭 하락"
            else:
                market_mood = "뚜렷한 하락"
        else:
            market_mood = "등락 혼조"
        
        # Index quote summary.
        indices_text = ""
        for idx in overview.indices[:4]:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            indices_text += f"- **{idx.name}**: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)\n"
        
        # Sector summary.
        top_text = ", ".join([s['name'] for s in overview.top_sectors[:3]])
        bottom_text = ", ".join([s['name'] for s in overview.bottom_sectors[:3]])
        
        # Include breadth and sector sections only for regions that provide them.
        stats_section = ""
        if self.profile.has_market_stats:
            stats_section = f"""
### 3. 등락 통계
| 지표 | 값 |
|------|------|
| 상승 종목 수 | {overview.up_count} |
| 하락 종목 수 | {overview.down_count} |
| 상한가 | {overview.limit_up_count} |
| 하한가 | {overview.limit_down_count} |
| 거래대금 | {overview.total_amount:.0f}억 |
"""
        sector_section = ""
        if self.profile.has_sector_rankings and (top_text or bottom_text):
            sector_section = f"""
### 4. 업종 동향
- **강세**: {top_text}
- **약세**: {bottom_text}
"""
        market_label = "한국 시장" if self.region == "kr" else "US market"
        strategy_summary = self.strategy.to_markdown_block()
        report = f"""## {overview.date} 시장 리캡

### 1. 시장 요약
오늘 {market_label}은 전반적으로 **{market_mood}** 흐름을 보였습니다.

### 2. 주요 지수
{indices_text}
{stats_section}
{sector_section}
### 5. 리스크 점검
시장은 변동성이 있습니다. 위 데이터는 참고용이며 투자 조언이 아닙니다.

{strategy_summary}

---
*리캡 시간: {datetime.now().strftime('%H:%M')}*
"""
        return report
    
    def run_daily_review(self) -> str:
        """
        Run the daily market recap workflow.
        
        Returns:
            Market recap report text.
        """
        logger.info("========== Starting market recap analysis ==========")
        
        # 1. Fetch market overview.
        overview = self.get_market_overview()
        
        # 2. Search market news.
        news = self.search_market_news()
        
        # 3. Generate recap report.
        report = self.generate_market_review(overview, news)
        
        logger.info("========== Market recap analysis completed ==========")
        
        return report


# Manual test entry point.
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    analyzer = MarketAnalyzer()
    
    # Fetch market overview.
    overview = analyzer.get_market_overview()
    print(f"\n=== 시장 개요 ===")
    print(f"날짜: {overview.date}")
    print(f"지수 수: {len(overview.indices)}")
    for idx in overview.indices:
        print(f"  {idx.name}: {idx.current:.2f} ({idx.change_pct:+.2f}%)")
    print(f"상승: {overview.up_count} | 하락: {overview.down_count}")
    print(f"거래대금: {overview.total_amount:.0f}억")
    
    # Generate a template report.
    report = analyzer._generate_template_review(overview, [])
    print(f"\n=== 리캡 보고서 ===")
    print(report)

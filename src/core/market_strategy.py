# -*- coding: utf-8 -*-
"""Market strategy blueprints for KR/US daily market recap."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StrategyDimension:
    """Single strategy dimension used by market recap prompts."""

    name: str
    objective: str
    checkpoints: List[str]


@dataclass(frozen=True)
class MarketStrategyBlueprint:
    """Region specific market strategy blueprint."""

    region: str
    title: str
    positioning: str
    principles: List[str]
    dimensions: List[StrategyDimension]
    action_framework: List[str]

    def to_prompt_block(self) -> str:
        """Render blueprint as prompt instructions."""
        principles_text = "\n".join([f"- {item}" for item in self.principles])
        action_text = "\n".join([f"- {item}" for item in self.action_framework])

        dims = []
        for dim in self.dimensions:
            checkpoints = "\n".join([f"  - {cp}" for cp in dim.checkpoints])
            dims.append(f"- {dim.name}: {dim.objective}\n{checkpoints}")
        dimensions_text = "\n".join(dims)

        return (
            f"## Strategy Blueprint: {self.title}\n"
            f"{self.positioning}\n\n"
            f"### Strategy Principles\n{principles_text}\n\n"
            f"### Analysis Dimensions\n{dimensions_text}\n\n"
            f"### Action Framework\n{action_text}"
        )

    def to_markdown_block(self) -> str:
        """Render blueprint as markdown section for template fallback report."""
        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### 六、전략 프레임워크" if self.region == "kr" else "### VI. Strategy Framework"
        return f"{section_title}\n{dims}\n"


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

US_BLUEPRINT = MarketStrategyBlueprint(
    region="us",
    title="US Market Regime Strategy",
    positioning="Focus on index trend, macro narrative, and sector rotation to define next-session risk posture.",
    principles=[
        "Read market regime from S&P 500, Nasdaq, and Dow alignment first.",
        "Separate beta move from theme-driven alpha rotation.",
        "Translate recap into actionable risk-on/risk-off stance with clear invalidation points.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Regime",
            objective="Classify the market as momentum, range, or risk-off.",
            checkpoints=[
                "Are SPX/NDX/DJI directionally aligned",
                "Did volume confirm the move",
                "Are key index levels reclaimed or lost",
            ],
        ),
        StrategyDimension(
            name="Macro & Flows",
            objective="Map policy/rates narrative into equity risk appetite.",
            checkpoints=[
                "Treasury yield and USD implications",
                "Breadth and leadership concentration",
                "Defensive vs growth factor rotation",
            ],
        ),
        StrategyDimension(
            name="Sector Themes",
            objective="Identify persistent leaders and vulnerable laggards.",
            checkpoints=[
                "AI/semiconductor/software trend persistence",
                "Energy/financials sensitivity to macro data",
                "Volatility signals from VIX and large-cap earnings",
            ],
        ),
    ],
    action_framework=[
        "Risk-on: broad index breakout with expanding participation.",
        "Neutral: mixed index signals; focus on selective relative strength.",
        "Risk-off: failed breakouts and rising volatility; prioritize capital preservation.",
    ],
)


def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    return US_BLUEPRINT if region == "us" else KR_BLUEPRINT

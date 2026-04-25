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
            f"## 전략 청사진: {self.title}\n"
            f"{self.positioning}\n\n"
            f"### 전략 원칙\n{principles_text}\n\n"
            f"### 분석 차원\n{dimensions_text}\n\n"
            f"### 실행 프레임워크\n{action_text}"
        )

    def to_markdown_block(self) -> str:
        """Render blueprint as markdown section for template fallback report."""
        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### 6. 전략 프레임워크" if self.region == "kr" else "### VI. 전략 프레임워크"
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
    title="미국 시장 국면 전략",
    positioning="지수 추세, 매크로 내러티브, 섹터 순환을 중심으로 다음 세션의 리스크 포지션을 정의합니다.",
    principles=[
        "먼저 S&P 500, Nasdaq, Dow의 방향 일치 여부로 시장 국면을 읽습니다.",
        "시장 베타 움직임과 테마 기반 알파 순환을 구분합니다.",
        "복기 결과를 명확한 무효화 기준이 있는 실행 가능한 리스크온/리스크오프 관점으로 전환합니다.",
    ],
    dimensions=[
        StrategyDimension(
            name="추세 국면",
            objective="시장을 모멘텀, 박스권, 리스크오프 중 하나로 분류합니다.",
            checkpoints=[
                "SPX/NDX/DJI의 방향이 일치하는지",
                "거래량이 움직임을 확인해 주는지",
                "주요 지수 레벨을 회복했는지 또는 이탈했는지",
            ],
        ),
        StrategyDimension(
            name="매크로와 자금 흐름",
            objective="정책 및 금리 내러티브를 주식 위험 선호도로 연결합니다.",
            checkpoints=[
                "미국 국채 금리와 달러 흐름의 시사점",
                "시장 폭과 주도주 집중도",
                "방어주와 성장주 팩터 순환",
            ],
        ),
        StrategyDimension(
            name="섹터 테마",
            objective="지속 가능한 주도 섹터와 취약한 후행 섹터를 식별합니다.",
            checkpoints=[
                "AI/반도체/소프트웨어 추세의 지속성",
                "에너지/금융 섹터의 매크로 데이터 민감도",
                "VIX와 대형주 실적에서 나타나는 변동성 신호",
            ],
        ),
    ],
    action_framework=[
        "리스크온: 주요 지수 돌파와 참여 종목 확산이 함께 나타나는 경우.",
        "중립: 지수 신호가 엇갈릴 때는 선별적 상대 강도에 집중합니다.",
        "리스크오프: 돌파 실패와 변동성 상승이 나타나면 자본 보존을 우선합니다.",
    ],
)


def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    return US_BLUEPRINT if region == "us" else KR_BLUEPRINT

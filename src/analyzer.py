# -*- coding: utf-8 -*-
"""
===================================
주식 분석 시스템 - AI 분석 레이어
===================================

기능:
1. LLM 호출 로직 캡슐화 (LiteLLM을 통해 Gemini/Anthropic/OpenAI 등 통합 호출)
2. 기술적 분석과 뉴스를 결합한 분석 리포트 생성
3. LLM 응답을 구조화된 AnalysisResult로 파싱
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

import litellm
from json_repair import repair_json
from litellm import Router

from src.agent.llm_adapter import get_thinking_extra_body
from src.config import Config, get_config, get_api_keys_for_model, extra_litellm_params

logger = logging.getLogger(__name__)


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

    Args:
        stock_code: 종목 코드
        context: 분석 컨텍스트 (선택)
        data_manager: DataFetcherManager 인스턴스 (선택)

    Returns:
        종목 이름
    """
    # 1. 컨텍스트에서 조회 (실시간 데이터)
    if context:
        # 우선 stock_name 필드에서 조회
        if context.get('stock_name'):
            name = context['stock_name']
            if name and not name.startswith('종목'):
                return name

        # 다음으로 realtime 데이터에서 조회
        if 'realtime' in context and context['realtime'].get('name'):
            return context['realtime']['name']

    # 2. 정적 매핑 테이블에서 조회
    if stock_code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[stock_code]

    # 3. 데이터 소스에서 조회
    if data_manager is None:
        try:
            from data_provider.base import DataFetcherManager
            data_manager = DataFetcherManager()
        except Exception as e:
            logger.debug(f"DataFetcherManager 초기화 불가: {e}")

    if data_manager:
        try:
            name = data_manager.get_stock_name(stock_code)
            if name:
                # 캐시 업데이트
                STOCK_NAME_MAP[stock_code] = name
                return name
        except Exception as e:
            logger.debug(f"데이터 소스에서 종목 이름 조회 실패: {e}")

    # 4. 기본 이름 반환
    return f'종목{stock_code}'


@dataclass
class AnalysisResult:
    """
    AI 분석 결과 데이터 클래스 - 의사결정 대시보드 버전

    Gemini 반환 분석 결과를 캡슐화, 의사결정 대시보드 및 상세 분석 포함
    """
    code: str
    name: str

    # ========== 핵심 지표 ==========
    sentiment_score: int  # 종합 점수 0-100 (>70 강력 매수, >60 매수, 40-60 횡보, <40 매도)
    trend_prediction: str  # 추세 예측: 강력 매수/매수/횡보/매도/강력 매도
    operation_advice: str  # 운용 제안: 매수/추가매수/보유/비중축소/매도/관망
    decision_type: str = "hold"  # 결정 유형: buy/hold/sell (통계용)
    confidence_level: str = "보통"  # 신뢰도: 높음/보통/낮음

    # ========== 의사결정 대시보드 ==========
    dashboard: Optional[Dict[str, Any]] = None  # 전체 의사결정 대시보드 데이터

    # ========== 추세 분석 ==========
    trend_analysis: str = ""  # 추세 형태 분석 (지지선, 저항선, 추세선 등)
    short_term_outlook: str = ""  # 단기 전망 (1-3일)
    medium_term_outlook: str = ""  # 중기 전망 (1-2주)

    # ========== 기술적 분석 ==========
    technical_analysis: str = ""  # 기술 지표 종합 분석
    ma_analysis: str = ""  # 이동평균선 분석 (정배열/역배열, 골든크로스/데드크로스 등)
    volume_analysis: str = ""  # 거래량 분석 (거래량 증가/감소, 주력 동향 등)
    pattern_analysis: str = ""  # 캔들 패턴 분석

    # ========== 기본적 분석 ==========
    fundamental_analysis: str = ""  # 기본적 분석 종합
    sector_position: str = ""  # 업종 지위 및 산업 추세
    company_highlights: str = ""  # 기업 하이라이트/리스크

    # ========== 심리/뉴스 분석 ==========
    news_summary: str = ""  # 최근 주요 뉴스/공시 요약
    market_sentiment: str = ""  # 시장 심리 분석
    hot_topics: str = ""  # 관련 이슈

    # ========== 종합 분석 ==========
    analysis_summary: str = ""  # 종합 분석 요약
    key_points: str = ""  # 핵심 포인트 (3-5개)
    risk_warning: str = ""  # 리스크 경고
    buy_reason: str = ""  # 매수/매도 근거

    # ========== 메타데이터 ==========
    market_snapshot: Optional[Dict[str, Any]] = None  # 당일 시장 스냅샷 (표시용)
    raw_response: Optional[str] = None  # 원시 응답 (디버그용)
    search_performed: bool = False  # 인터넷 검색 실행 여부
    data_sources: str = ""  # 데이터 출처 설명
    success: bool = True
    error_message: Optional[str] = None

    # ========== 가격 데이터 (분석 시 스냅샷) ==========
    current_price: Optional[float] = None  # 분석 시 주가
    change_pct: Optional[float] = None     # 분석 시 등락률(%)

    # ========== 모델 표기 (Issue #528) ==========
    model_used: Optional[str] = None  # 분석에 사용된 LLM 모델 (전체 이름, 예: gemini/gemini-2.0-flash)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'code': self.code,
            'name': self.name,
            'sentiment_score': self.sentiment_score,
            'trend_prediction': self.trend_prediction,
            'operation_advice': self.operation_advice,
            'decision_type': self.decision_type,
            'confidence_level': self.confidence_level,
            'dashboard': self.dashboard,  # 의사결정 대시보드 데이터
            'trend_analysis': self.trend_analysis,
            'short_term_outlook': self.short_term_outlook,
            'medium_term_outlook': self.medium_term_outlook,
            'technical_analysis': self.technical_analysis,
            'ma_analysis': self.ma_analysis,
            'volume_analysis': self.volume_analysis,
            'pattern_analysis': self.pattern_analysis,
            'fundamental_analysis': self.fundamental_analysis,
            'sector_position': self.sector_position,
            'company_highlights': self.company_highlights,
            'news_summary': self.news_summary,
            'market_sentiment': self.market_sentiment,
            'hot_topics': self.hot_topics,
            'analysis_summary': self.analysis_summary,
            'key_points': self.key_points,
            'risk_warning': self.risk_warning,
            'buy_reason': self.buy_reason,
            'market_snapshot': self.market_snapshot,
            'search_performed': self.search_performed,
            'success': self.success,
            'error_message': self.error_message,
            'current_price': self.current_price,
            'change_pct': self.change_pct,
            'model_used': self.model_used,
        }

    def get_core_conclusion(self) -> str:
        """핵심 결론 조회 (한 줄)"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            return self.dashboard['core_conclusion'].get('one_sentence', self.analysis_summary)
        return self.analysis_summary

    def get_position_advice(self, has_position: bool = False) -> str:
        """보유 포지션 조언 조회"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            pos_advice = self.dashboard['core_conclusion'].get('position_advice', {})
            if has_position:
                return pos_advice.get('has_position', self.operation_advice)
            return pos_advice.get('no_position', self.operation_advice)
        return self.operation_advice

    def get_sniper_points(self) -> Dict[str, str]:
        """매매 포인트 조회"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('sniper_points', {})
        return {}

    def get_checklist(self) -> List[str]:
        """체크리스트 조회"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('action_checklist', [])
        return []

    def get_risk_alerts(self) -> List[str]:
        """리스크 경고 조회"""
        if self.dashboard and 'intelligence' in self.dashboard:
            return self.dashboard['intelligence'].get('risk_alerts', [])
        return []

    def get_emoji(self) -> str:
        """운용 제안에 대응하는 emoji 반환"""
        emoji_map = {
            '매수': '🟢',
            '추가매수': '🟢',
            '강력 매수': '💚',
            '보유': '🟡',
            '관망': '⚪',
            '비중축소': '🟠',
            '매도': '🔴',
            '강력 매도': '❌',
        }
        advice = self.operation_advice or ''
        # Direct match first
        if advice in emoji_map:
            return emoji_map[advice]
        # Handle compound advice like "매도/관망" — use the first part
        for part in advice.replace('/', '|').split('|'):
            part = part.strip()
            if part in emoji_map:
                return emoji_map[part]
        # Score-based fallback
        score = self.sentiment_score
        if score >= 80:
            return '💚'
        elif score >= 65:
            return '🟢'
        elif score >= 55:
            return '🟡'
        elif score >= 45:
            return '⚪'
        elif score >= 35:
            return '🟠'
        else:
            return '🔴'

    def get_confidence_stars(self) -> str:
        """신뢰도 별점 반환"""
        star_map = {'높음': '⭐⭐⭐', '보통': '⭐⭐', '낮음': '⭐'}
        return star_map.get(self.confidence_level, '⭐⭐')


class GeminiAnalyzer:
    """
    Gemini AI 분석기

    역할:
    1. Google Gemini API를 호출하여 주식 분석 수행
    2. 사전 검색된 뉴스 및 기술적 데이터를 결합하여 분석 리포트 생성
    3. AI 반환 JSON 형식 결과 파싱

    사용 방법:
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze(context, news_context)
    """

    # ========================================
    # 시스템 프롬프트 - 의사결정 대시보드 v2.0
    # ========================================
    # 출력 형식 업그레이드: 단순 신호 → 의사결정 대시보드
    # 핵심 모듈: 핵심 결론 + 데이터 투시 + 뉴스 정보 + 전략 계획
    # ========================================

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
                "current_price": 현재가,
                "ma5": MA5,
                "ma10": MA10,
                "ma20": MA20,
                "bias_ma5": 이격률,
                "bias_status": "안전/경계/위험",
                "support_level": 지지선,
                "resistance_level": 저항선
            },
            "volume_analysis": {
                "volume_ratio": 거래량비율,
                "volume_status": "거래량증가/거래량감소/보통",
                "turnover_rate": 회전율,
                "volume_meaning": "거래량 의미 해석"
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
            "earnings_outlook": "실적 전망 분석",
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
                "✅/⚠️/❌ 체크 2: 이격률 적정",
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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM Analyzer via LiteLLM.

        Args:
            api_key: Ignored (kept for backward compatibility). Keys are loaded from config.
        """
        self._router = None
        self._litellm_available = False
        self._init_litellm()
        if not self._litellm_available:
            logger.warning("No LLM configured (LITELLM_MODEL / API keys), AI analysis will be unavailable")

    def _has_channel_config(self, config: Config) -> bool:
        """Check if multi-channel config (channels / YAML / legacy model_list) is active."""
        return bool(config.llm_model_list) and not all(
            e.get('model_name', '').startswith('__legacy_') for e in config.llm_model_list
        )

    def _init_litellm(self) -> None:
        """Initialize litellm Router from channels / YAML / legacy keys."""
        config = get_config()
        litellm_model = config.litellm_model
        if not litellm_model:
            logger.warning("Analyzer LLM: LITELLM_MODEL not configured")
            return

        self._litellm_available = True

        # --- Channel / YAML path: build Router from pre-built model_list ---
        if self._has_channel_config(config):
            model_list = config.llm_model_list
            self._router = Router(
                model_list=model_list,
                routing_strategy="simple-shuffle",
                num_retries=2,
            )
            unique_models = list(dict.fromkeys(
                e['litellm_params']['model'] for e in model_list
            ))
            logger.info(
                f"Analyzer LLM: Router initialized from channels/YAML — "
                f"{len(model_list)} deployment(s), models: {unique_models}"
            )
            return

        # --- Legacy path: build Router for multi-key, or use single key ---
        keys = get_api_keys_for_model(litellm_model, config)

        if len(keys) > 1:
            # Build legacy Router for primary model multi-key load-balancing
            extra_params = extra_litellm_params(litellm_model, config)
            legacy_model_list = [
                {
                    "model_name": litellm_model,
                    "litellm_params": {
                        "model": litellm_model,
                        "api_key": k,
                        **extra_params,
                    },
                }
                for k in keys
            ]
            self._router = Router(
                model_list=legacy_model_list,
                routing_strategy="simple-shuffle",
                num_retries=2,
            )
            logger.info(
                f"Analyzer LLM: Legacy Router initialized with {len(keys)} keys "
                f"for {litellm_model}"
            )
        elif keys:
            logger.info(f"Analyzer LLM: litellm initialized (model={litellm_model})")
        else:
            logger.info(
                f"Analyzer LLM: litellm initialized (model={litellm_model}, "
                f"API key from environment)"
            )

    def is_available(self) -> bool:
        """Check if LiteLLM is properly configured with at least one API key."""
        return self._router is not None or self._litellm_available

    def _call_litellm(self, prompt: str, generation_config: dict) -> Tuple[str, str]:
        """Call LLM via litellm with fallback across configured models.

        When channels/YAML are configured, every model goes through the Router
        (which handles per-model key selection, load balancing, and retries).
        In legacy mode, the primary model may use the Router while fallback
        models fall back to direct litellm.completion().

        Args:
            prompt: User prompt text.
            generation_config: Dict with optional keys: temperature, max_output_tokens, max_tokens.

        Returns:
            Tuple of (response text, model_used). On success model_used is the full model name.
        """
        config = get_config()
        max_tokens = (
            generation_config.get('max_output_tokens')
            or generation_config.get('max_tokens')
            or 8192
        )
        temperature = generation_config.get('temperature', 0.7)

        models_to_try = [config.litellm_model] + (config.litellm_fallback_models or [])
        models_to_try = [m for m in models_to_try if m]

        use_channel_router = self._has_channel_config(config)

        last_error = None
        for model in models_to_try:
            try:
                model_short = model.split("/")[-1] if "/" in model else model
                call_kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                extra = get_thinking_extra_body(model_short)
                if extra:
                    call_kwargs["extra_body"] = extra

                if use_channel_router and self._router:
                    # Channel / YAML path: Router manages key + base_url per model
                    response = self._router.completion(**call_kwargs)
                elif self._router and model == config.litellm_model:
                    # Legacy path: Router only for primary model multi-key
                    response = self._router.completion(**call_kwargs)
                else:
                    # Legacy path: direct call for fallback models
                    keys = get_api_keys_for_model(model, config)
                    if keys:
                        call_kwargs["api_key"] = keys[0]
                    call_kwargs.update(extra_litellm_params(model, config))
                    response = litellm.completion(**call_kwargs)

                if response and response.choices and response.choices[0].message.content:
                    return (response.choices[0].message.content, model)
                raise ValueError("LLM returned empty response")

            except Exception as e:
                logger.warning(f"[LiteLLM] {model} failed: {e}")
                last_error = e
                continue

        raise Exception(f"All LLM models failed (tried {len(models_to_try)} model(s)). Last error: {last_error}")

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Public entry point for free-form text generation.

        External callers (e.g. MarketAnalyzer) must use this method instead of
        calling _call_litellm() directly or accessing private attributes such as
        _litellm_available, _router, _model, _use_openai, or _use_anthropic.

        Args:
            prompt:      Text prompt to send to the LLM.
            max_tokens:  Maximum tokens in the response (default 2048).
            temperature: Sampling temperature (default 0.7).

        Returns:
            Response text, or None if the LLM call fails (error is logged).
        """
        try:
            result = self._call_litellm(
                prompt,
                generation_config={"max_tokens": max_tokens, "temperature": temperature},
            )
            return result[0] if isinstance(result, tuple) else result
        except Exception as exc:
            logger.error("[generate_text] LLM call failed: %s", exc)
            return None

    def analyze(
        self, 
        context: Dict[str, Any],
        news_context: Optional[str] = None
    ) -> AnalysisResult:
        """
        단일 종목 분석

        처리 흐름:
        1. 입력 데이터 포맷 (기술적 분석 + 뉴스)
        2. Gemini API 호출 (재시도 및 모델 전환 포함)
        3. JSON 응답 파싱
        4. 구조화된 결과 반환

        Args:
            context: storage.get_analysis_context()에서 가져온 컨텍스트 데이터
            news_context: 사전 검색된 뉴스 내용 (선택)

        Returns:
            AnalysisResult 객체
        """
        code = context.get('code', 'Unknown')
        config = get_config()

        # 요청 전 지연 추가 (연속 요청 시 속도 제한 방지)
        request_delay = config.gemini_request_delay
        if request_delay > 0:
            logger.debug(f"[LLM] 요청 전 {request_delay:.1f}초 대기...")
            time.sleep(request_delay)

        # 컨텍스트에서 종목 이름 우선 조회 (main.py에서 전달)
        name = context.get('stock_name')
        if not name or name.startswith('종목'):
            # 대안: realtime에서 조회
            if 'realtime' in context and context['realtime'].get('name'):
                name = context['realtime']['name']
            else:
                # 마지막으로 매핑 테이블에서 조회
                name = STOCK_NAME_MAP.get(code, f'종목{code}')

        # 모델 사용 불가 시 기본 결과 반환
        if not self.is_available():
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction='횡보',
                operation_advice='보유',
                confidence_level='낮음',
                analysis_summary='AI 분석 기능 미활성화 (API Key 미설정)',
                risk_warning='LLM API Key (GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY)를 설정 후 재시도하세요',
                success=False,
                error_message='LLM API Key 미설정',
                model_used=None,
            )

        try:
            # 입력 포맷 (기술적 데이터 + 뉴스 포함)
            prompt = self._format_prompt(context, name, news_context)

            config = get_config()
            model_name = config.litellm_model or "unknown"
            logger.info(f"========== AI 분석 {name}({code}) ==========")
            logger.info(f"[LLM 설정] 모델: {model_name}")
            logger.info(f"[LLM 설정] 프롬프트 길이: {len(prompt)}자")
            logger.info(f"[LLM 설정] 뉴스 포함 여부: {'예' if news_context else '아니오'}")

            # 로그에 전체 프롬프트 기록 (INFO 레벨: 요약, DEBUG: 전체)
            prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.info(f"[LLM 프롬프트 미리보기]\n{prompt_preview}")
            logger.debug(f"=== 전체 프롬프트 ({len(prompt)}자) ===\n{prompt}\n=== 프롬프트 끝 ===")

            # 생성 설정
            generation_config = {
                "temperature": config.gemini_temperature,
                "max_output_tokens": 8192,
            }

            logger.info(f"[LLM 호출] {model_name} 호출 시작...")

            # litellm으로 호출
            start_time = time.time()
            response_text, model_used = self._call_litellm(prompt, generation_config)
            elapsed = time.time() - start_time

            # 응답 정보 기록
            logger.info(f"[LLM 응답] {model_name} 응답 성공, 소요 {elapsed:.2f}초, 응답 길이 {len(response_text)}자")

            # 응답 미리보기 기록 (INFO) 및 전체 응답 (DEBUG)
            response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
            logger.info(f"[LLM 응답 미리보기]\n{response_preview}")
            logger.debug(f"=== {model_name} 전체 응답 ({len(response_text)}자) ===\n{response_text}\n=== 응답 끝 ===")

            # 응답 파싱
            result = self._parse_response(response_text, code, name)
            result.raw_response = response_text
            result.search_performed = bool(news_context)
            result.market_snapshot = self._build_market_snapshot(context)
            result.model_used = model_used

            logger.info(f"[LLM 파싱] {name}({code}) 분석 완료: {result.trend_prediction}, 점수 {result.sentiment_score}")

            return result

        except Exception as e:
            logger.error(f"AI 분석 {name}({code}) 실패: {e}")
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction='횡보',
                operation_advice='보유',
                confidence_level='낮음',
                analysis_summary=f'분석 중 오류 발생: {str(e)[:100]}',
                risk_warning='분석 실패. 나중에 다시 시도하거나 수동으로 분석하세요',
                success=False,
                error_message=str(e),
                model_used=None,
            )
    
    def _format_prompt(
        self,
        context: Dict[str, Any],
        name: str,
        news_context: Optional[str] = None
    ) -> str:
        """
        분석 프롬프트 생성 (의사결정 대시보드 v2.0)

        포함 항목: 기술 지표, 실시간 시세(거래량비율/회전율), 수급 분포, 추세 분석, 뉴스

        Args:
            context: 기술적 데이터 컨텍스트 (강화 데이터 포함)
            name:    종목명 (기본값, 컨텍스트에서 덮어쓸 수 있음)
            news_context: 사전 검색된 뉴스 내용
        """
        code = context.get('code', 'Unknown')

        # 컨텍스트의 종목명 우선 사용 (realtime_quote에서 가져옴)
        stock_name = context.get('stock_name', name)
        if not stock_name or stock_name == f'주식{code}':
            stock_name = STOCK_NAME_MAP.get(code, f'종목{code}')

        today = context.get('today', {})

        # ========== 의사결정 대시보드 형식 프롬프트 구성 ==========
        prompt = f"""# 의사결정 대시보드 분석 요청

## 📊 종목 기본 정보
| 항목 | 데이터 |
|------|------|
| 종목 코드 | **{code}** |
| 종목명 | **{stock_name}** |
| 분석 날짜 | {context.get('date', '알 수 없음')} |

---

## 📈 기술적 데이터

### 당일 시세
| 지표 | 수치 |
|------|------|
| 종가 | {today.get('close', 'N/A')} |
| 시가 | {today.get('open', 'N/A')} |
| 고가 | {today.get('high', 'N/A')} |
| 저가 | {today.get('low', 'N/A')} |
| 등락률 | {today.get('pct_chg', 'N/A')}% |
| 거래량 | {self._format_volume(today.get('volume'))} |
| 거래대금 | {self._format_amount(today.get('amount'))} |

### 이동평균선 시스템 (핵심 판단 지표)
| 이평선 | 수치 | 설명 |
|------|------|------|
| MA5 | {today.get('ma5', 'N/A')} | 단기 추세선 |
| MA10 | {today.get('ma10', 'N/A')} | 단중기 추세선 |
| MA20 | {today.get('ma20', 'N/A')} | 중기 추세선 |
| 이평선 형태 | {context.get('ma_status', '알 수 없음')} | 정배열/역배열/혼조 |
"""

        # 실시간 시세 강화 데이터 추가 (거래량비율, 회전율 등)
        if 'realtime' in context:
            rt = context['realtime']
            prompt += f"""
### 실시간 시세 강화 데이터
| 지표 | 수치 | 해석 |
|------|------|------|
| 현재가 | {rt.get('price', 'N/A')} | |
| **거래량비율** | **{rt.get('volume_ratio', 'N/A')}** | {rt.get('volume_ratio_desc', '')} |
| **회전율** | **{rt.get('turnover_rate', 'N/A')}%** | |
| PER(동적) | {rt.get('pe_ratio', 'N/A')} | |
| PBR | {rt.get('pb_ratio', 'N/A')} | |
| 시가총액 | {self._format_amount(rt.get('total_mv'))} | |
| 유통시가총액 | {self._format_amount(rt.get('circ_mv'))} | |
| 60일 등락률 | {rt.get('change_60d', 'N/A')}% | 중기 성과 |
"""

        # 수급 분포 데이터 추가
        if 'chip' in context:
            chip = context['chip']
            profit_ratio = chip.get('profit_ratio', 0)
            prompt += f"""
### 수급 분포 데이터 (효율 지표)
| 지표 | 수치 | 건강 기준 |
|------|------|----------|
| **수익 비율** | **{profit_ratio:.1%}** | 70-90% 구간 주의 |
| 평균 매수단가 | {chip.get('avg_cost', 'N/A')} | 현재가가 5-15% 이상이어야 함 |
| 90% 수급 집중도 | {chip.get('concentration_90', 0):.2%} | <15% 집중 |
| 70% 수급 집중도 | {chip.get('concentration_70', 0):.2%} | |
| 수급 상태 | {chip.get('chip_status', '알 수 없음')} | |
"""

        # 추세 분석 결과 추가 (매매 원칙 기반 사전 판단)
        if 'trend_analysis' in context:
            trend = context['trend_analysis']
            bias_warning = "🚨 5% 초과 — 고점 추격 금지!" if trend.get('bias_ma5', 0) > 5 else "✅ 안전 범위"
            prompt += f"""
### 추세 분석 사전 판단 (매매 원칙 기반)
| 지표 | 수치 | 판정 |
|------|------|------|
| 추세 상태 | {trend.get('trend_status', '알 수 없음')} | |
| 이평선 배열 | {trend.get('ma_alignment', '알 수 없음')} | MA5>MA10>MA20 정배열 |
| 추세 강도 | {trend.get('trend_strength', 0)}/100 | |
| **이격률(MA5)** | **{trend.get('bias_ma5', 0):+.2f}%** | {bias_warning} |
| 이격률(MA10) | {trend.get('bias_ma10', 0):+.2f}% | |
| 거래량 상태 | {trend.get('volume_status', '알 수 없음')} | {trend.get('volume_trend', '')} |
| 시스템 신호 | {trend.get('buy_signal', '알 수 없음')} | |
| 시스템 점수 | {trend.get('signal_score', 0)}/100 | |

#### 시스템 분석 근거
**매수 근거:**
{chr(10).join('- ' + r for r in trend.get('signal_reasons', ['없음'])) if trend.get('signal_reasons') else '- 없음'}

**리스크 요인:**
{chr(10).join('- ' + r for r in trend.get('risk_factors', ['없음'])) if trend.get('risk_factors') else '- 없음'}
"""

        # 전일 대비 데이터 추가
        if 'yesterday' in context:
            volume_change = context.get('volume_change_ratio', 'N/A')
            prompt += f"""
### 거래량/가격 변화
- 거래량 전일 대비: {volume_change}배
- 가격 전일 대비: {context.get('price_change_ratio', 'N/A')}%
"""

        # 뉴스 검색 결과 추가
        prompt += """
---

## 📰 뉴스 및 시장 정보
"""
        if news_context:
            prompt += f"""
아래는 **{stock_name}({code})** 최근 7일 뉴스 검색 결과입니다. 다음 항목을 중점 추출하세요:
1. 🚨 **리스크 경보**: 대량 매도, 제재, 악재
2. 🎯 **호재 촉매**: 실적, 계약, 정책
3. 📊 **실적 전망**: 사전 공시, 실적 속보

```
{news_context}
```
"""
        else:
            prompt += """
해당 종목의 최근 뉴스를 찾을 수 없습니다. 기술적 데이터를 중심으로 분석하세요.
"""

        # 데이터 누락 경고 주입
        if context.get('data_missing'):
            prompt += """
⚠️ **데이터 누락 경고**
인터페이스 제한으로 인해 전체 실시간 시세 및 기술 지표 데이터를 가져올 수 없습니다.
위 표의 **N/A 데이터는 무시**하고, **【📰 뉴스 및 시장 정보】** 의 뉴스를 중심으로 기본적·심리적 분석을 수행하세요.
기술적 질문(이평선, 이격률 등)에 대해서는 "데이터 누락으로 판단 불가"라고 직접 명시하고, **데이터를 임의로 생성하지 마세요**.
"""

        # 출력 요구사항 명시
        prompt += f"""
---

## ✅ 분석 작업

**{stock_name}({code})** 에 대한 【의사결정 대시보드】를 JSON 형식으로 출력하세요.
"""
        if context.get('is_index_etf'):
            prompt += """
> ⚠️ **지수/ETF 분석 제약**: 이 종목은 지수 추종 ETF 또는 시장 지수입니다.
> - 리스크 분석은 **지수 흐름, 추적 오차, 시장 유동성**만 다루세요.
> - 운용사의 소송, 평판, 임원 변경은 리스크 경보에 포함하지 마세요.
> - 실적 전망은 **지수 구성종목 전체 성과** 기준이며, 운용사 재무제표가 아닙니다.
> - `risk_alerts`에 펀드 운용사 관련 경영 리스크를 포함하지 마세요.

"""
        prompt += f"""
### ⚠️ 중요: 올바른 종목명 형식 출력
올바른 종목명 형식은 "종목명（종목 코드）"입니다. 예: "삼성전자（005930）".
위에 표시된 종목명이 "종목{code}" 또는 올바르지 않다면, 분석 시작 부분에 **올바른 한국어 전체 이름을 명확히 출력**하세요.

### 중점 확인 사항 (반드시 명확히 답변):
1. ❓ MA5>MA10>MA20 정배열 충족 여부?
2. ❓ 현재 이격률이 안전 범위(<5%) 이내인지? — 5% 초과 시 반드시 "고점 추격 금지" 표시
3. ❓ 거래량 뒷받침 여부 (거래량 감소 조정 / 거래량 증가 돌파)?
4. ❓ 수급 구조 건전성?
5. ❓ 뉴스에 중대 악재 있는지? (대량 매도, 제재, 실적 악화 등)

### 의사결정 대시보드 요구사항:
- **종목명**: 올바른 한국어 전체 이름 출력 (예: "종목005930" 불가, "삼성전자" 가능)
- **핵심 결론**: 매수/매도/대기 여부를 한 문장으로
- **포지션 분류 제안**: 미보유자 대응 vs 보유자 대응
- **구체적 저격 포인트**: 매수가, 손절가, 목표가 (정확한 수치)
- **확인 체크리스트**: 각 항목에 ✅/⚠️/❌ 표시

JSON 형식의 전체 의사결정 대시보드를 출력하세요."""

        return prompt

    def _format_volume(self, volume: Optional[float]) -> str:
        """거래량 포맷 출력"""
        if volume is None:
            return 'N/A'
        if volume >= 1e8:
            return f"{volume / 1e8:.2f} 억주"
        elif volume >= 1e4:
            return f"{volume / 1e4:.2f} 만주"
        else:
            return f"{volume:.0f} 주"

    def _format_amount(self, amount: Optional[float]) -> str:
        """거래대금 포맷 출력"""
        if amount is None:
            return 'N/A'
        if amount >= 1e12:
            return f"{amount / 1e12:.2f} 조원"
        elif amount >= 1e8:
            return f"{amount / 1e8:.2f} 억원"
        elif amount >= 1e4:
            return f"{amount / 1e4:.2f} 만원"
        else:
            return f"{amount:.0f} 원"

    def _format_percent(self, value: Optional[float]) -> str:
        """형식化百分比표시"""
        if value is None:
            return 'N/A'
        try:
            return f"{float(value):.2f}%"
        except (TypeError, ValueError):
            return 'N/A'

    def _format_price(self, value: Optional[float]) -> str:
        """형식化가격표시"""
        if value is None:
            return 'N/A'
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return 'N/A'

    def _build_market_snapshot(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """构建当日시세快照（展示用）"""
        today = context.get('today', {}) or {}
        realtime = context.get('realtime', {}) or {}
        yesterday = context.get('yesterday', {}) or {}

        prev_close = yesterday.get('close')
        close = today.get('close')
        high = today.get('high')
        low = today.get('low')

        amplitude = None
        change_amount = None
        if prev_close not in (None, 0) and high is not None and low is not None:
            try:
                amplitude = (float(high) - float(low)) / float(prev_close) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                amplitude = None
        if prev_close is not None and close is not None:
            try:
                change_amount = float(close) - float(prev_close)
            except (TypeError, ValueError):
                change_amount = None

        snapshot = {
            "date": context.get('date', '알 수 없음'),
            "close": self._format_price(close),
            "open": self._format_price(today.get('open')),
            "high": self._format_price(high),
            "low": self._format_price(low),
            "prev_close": self._format_price(prev_close),
            "pct_chg": self._format_percent(today.get('pct_chg')),
            "change_amount": self._format_price(change_amount),
            "amplitude": self._format_percent(amplitude),
            "volume": self._format_volume(today.get('volume')),
            "amount": self._format_amount(today.get('amount')),
        }

        if realtime:
            snapshot.update({
                "price": self._format_price(realtime.get('price')),
                "volume_ratio": realtime.get('volume_ratio', 'N/A'),
                "turnover_rate": self._format_percent(realtime.get('turnover_rate')),
                "source": getattr(realtime.get('source'), 'value', realtime.get('source', 'N/A')),
            })

        return snapshot

    def _parse_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """
        파싱 Gemini 응답（决策仪表盘版）
        
        尝试从응답中提取 JSON 형식的분석결과，包含 dashboard 字段
        如果파싱실패，尝试지능형提取或반환기본값결과
        """
        try:
            # 清理응답텍스트：移除 markdown 코드块标记
            cleaned_text = response_text
            if '```json' in cleaned_text:
                cleaned_text = cleaned_text.replace('```json', '').replace('```', '')
            elif '```' in cleaned_text:
                cleaned_text = cleaned_text.replace('```', '')
            
            # 尝试找到 JSON 내용
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_text[json_start:json_end]
                
                # 尝试수정常见的 JSON 问题
                json_str = self._fix_json_string(json_str)
                
                data = json.loads(json_str)
                
                # 提取 dashboard 데이터
                dashboard = data.get('dashboard', None)

                # 优先사용 AI 반환的종목명（如果原이름无效或包含코드）
                ai_stock_name = data.get('stock_name')
                if ai_stock_name and (name.startswith('주식') or name == code or 'Unknown' in name):
                    name = ai_stock_name

                # 파싱所有字段，사용기본값防止缺失
                # 파싱 decision_type，如果没有则기준으로 operation_advice 推断
                decision_type = data.get('decision_type', '')
                if not decision_type:
                    op = data.get('operation_advice', '보유')
                    if op in ['매수', '加仓', '强烈매수']:
                        decision_type = 'buy'
                    elif op in ['매도', '减仓', '强烈매도']:
                        decision_type = 'sell'
                    else:
                        decision_type = 'hold'
                
                return AnalysisResult(
                    code=code,
                    name=name,
                    # 核心指标
                    sentiment_score=int(data.get('sentiment_score', 50)),
                    trend_prediction=data.get('trend_prediction', '震荡'),
                    operation_advice=data.get('operation_advice', '보유'),
                    decision_type=decision_type,
                    confidence_level=data.get('confidence_level', '中'),
                    # 决策仪表盘
                    dashboard=dashboard,
                    # 走势분석
                    trend_analysis=data.get('trend_analysis', ''),
                    short_term_outlook=data.get('short_term_outlook', ''),
                    medium_term_outlook=data.get('medium_term_outlook', ''),
                    # 技术面
                    technical_analysis=data.get('technical_analysis', ''),
                    ma_analysis=data.get('ma_analysis', ''),
                    volume_analysis=data.get('volume_analysis', ''),
                    pattern_analysis=data.get('pattern_analysis', ''),
                    # 基本面
                    fundamental_analysis=data.get('fundamental_analysis', ''),
                    sector_position=data.get('sector_position', ''),
                    company_highlights=data.get('company_highlights', ''),
                    # 情绪面/메시지面
                    news_summary=data.get('news_summary', ''),
                    market_sentiment=data.get('market_sentiment', ''),
                    hot_topics=data.get('hot_topics', ''),
                    # 综合
                    analysis_summary=data.get('analysis_summary', '분석완료'),
                    key_points=data.get('key_points', ''),
                    risk_warning=data.get('risk_warning', ''),
                    buy_reason=data.get('buy_reason', ''),
                    # 元데이터
                    search_performed=data.get('search_performed', False),
                    data_sources=data.get('data_sources', '技术面데이터'),
                    success=True,
                )
            else:
                # 没有找到 JSON，尝试从纯텍스트中提取정보
                logger.warning(f"无法从응답中提取 JSON，사용原始텍스트분석")
                return self._parse_text_response(response_text, code, name)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱실패: {e}，尝试从텍스트提取")
            return self._parse_text_response(response_text, code, name)
    
    def _fix_json_string(self, json_str: str) -> str:
        """수정常见的 JSON 형식问题"""
        import re
        
        # 移除注释
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 수정尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 确保布尔值是小写
        json_str = json_str.replace('True', 'true').replace('False', 'false')
        
        # fix by json-repair
        json_str = repair_json(json_str)
        
        return json_str
    
    def _parse_text_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """从纯텍스트응답中尽可能提取분석정보"""
        # 尝试识别关键词来판단情绪
        sentiment_score = 50
        trend = '震荡'
        advice = '보유'
        
        text_lower = response_text.lower()
        
        # 简单的情绪识别
        positive_keywords = ['강세', '매수', '上涨', '突破', '强势', '利好', '加仓', 'bullish', 'buy']
        negative_keywords = ['看空', '매도', '下跌', '跌破', '弱势', '利空', '减仓', 'bearish', 'sell']
        
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if positive_count > negative_count + 1:
            sentiment_score = 65
            trend = '강세'
            advice = '매수'
            decision_type = 'buy'
        elif negative_count > positive_count + 1:
            sentiment_score = 35
            trend = '看空'
            advice = '매도'
            decision_type = 'sell'
        else:
            decision_type = 'hold'
        
        # 截取前500字符作为요약
        summary = response_text[:500] if response_text else '无분석결과'
        
        return AnalysisResult(
            code=code,
            name=name,
            sentiment_score=sentiment_score,
            trend_prediction=trend,
            operation_advice=advice,
            decision_type=decision_type,
            confidence_level='低',
            analysis_summary=summary,
            key_points='JSON파싱실패，仅供参考',
            risk_warning='분석결과可能不准确，建议结合其他정보판단',
            raw_response=response_text,
            success=True,
        )
    
    def batch_analyze(
        self, 
        contexts: List[Dict[str, Any]],
        delay_between: float = 2.0
    ) -> List[AnalysisResult]:
        """
        일괄여러 종목 분석
        
        주의：为방지 API 速率限制，每次분석之间会有延迟
        
        Args:
            contexts: 上下文데이터목록
            delay_between: 每次분석之间的延迟（秒）
            
        Returns:
            AnalysisResult 목록
        """
        results = []
        
        for i, context in enumerate(contexts):
            if i > 0:
                logger.debug(f"等待 {delay_between} 秒后继续...")
                time.sleep(delay_between)
            
            result = self.analyze(context)
            results.append(result)
        
        return results


# 도우미 함수
def get_analyzer() -> GeminiAnalyzer:
    """가져오기 LLM 분석器인스턴스"""
    return GeminiAnalyzer()


if __name__ == "__main__":
    # 테스트코드
    logging.basicConfig(level=logging.DEBUG)
    
    # 模拟上下文데이터
    test_context = {
        'code': '600519',
        'date': '2026-01-09',
        'today': {
            'open': 1800.0,
            'high': 1850.0,
            'low': 1780.0,
            'close': 1820.0,
            'volume': 10000000,
            'amount': 18200000000,
            'pct_chg': 1.5,
            'ma5': 1810.0,
            'ma10': 1800.0,
            'ma20': 1790.0,
            'volume_ratio': 1.2,
        },
        'ma_status': '정배열 📈',
        'volume_change_ratio': 1.3,
        'price_change_ratio': 1.5,
    }
    
    analyzer = GeminiAnalyzer()
    
    if analyzer.is_available():
        print("=== AI 분석테스트 ===")
        result = analyzer.analyze(test_context)
        print(f"분석결과: {result.to_dict()}")
    else:
        print("Gemini API 未설정，跳过테스트")

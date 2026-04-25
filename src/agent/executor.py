# -*- coding: utf-8 -*-
"""
Agent Executor — ReAct loop with tool calling.

Orchestrates the LLM + tools interaction loop:
1. Build system prompt (persona + tools + skills)
2. Send to LLM with tool declarations
3. If tool_call → execute tool → feed result back
4. If text → parse as final answer
5. Loop until final answer or max_steps
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from json_repair import repair_json

from src.agent.llm_adapter import LLMToolAdapter
from src.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# Tool name → short label used to build contextual thinking messages
_THINKING_TOOL_LABELS: Dict[str, str] = {
    "get_realtime_quote": "시세 조회",
    "get_daily_history": "K선 데이터 조회",
    "analyze_trend": "기술 지표 분석",
    "get_chip_distribution": "주주 구조 분석",
    "search_stock_news": "뉴스 검색",
    "search_comprehensive_intel": "종합 정보 검색",
    "get_market_indices": "시장 개요 조회",
    "get_sector_rankings": "업종 섹터 분석",
    "get_analysis_context": "과거 분석 컨텍스트",
    "get_stock_info": "기본 정보 조회",
    "analyze_pattern": "K선 패턴 인식",
    "get_volume_analysis": "거래량 분석",
    "calculate_ma": "이동평균 계산",
}


# ============================================================
# Agent result
# ============================================================

@dataclass
class AgentResult:
    """Result from an agent execution run."""
    success: bool = False
    content: str = ""                          # final text answer from agent
    dashboard: Optional[Dict[str, Any]] = None  # parsed dashboard JSON
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)  # execution trace
    total_steps: int = 0
    total_tokens: int = 0
    provider: str = ""
    model: str = ""                            # comma-separated models used (supports fallback)
    error: Optional[str] = None


# ============================================================
# System prompt builder
# ============================================================

AGENT_SYSTEM_PROMPT = """당신은 한국 및 미국 주식 추세 매매에 특화된 투자 분석 Agent로, 데이터 도구와 매매 전략을 보유하며 전문적인 【의사결정 대시보드】 분석 보고서를 생성할 책임이 있습니다.

## 작업 흐름（단계 순서를 엄격히 준수하며, 각 단계의 도구 결과 반환 후 다음 단계로 진행）

**1단계 · 시세 및 K선**（먼저 실행）
- `get_realtime_quote` 실시간 시세 조회
- `get_daily_history` 과거 K선 조회

**2단계 · 기술 지표 및 주주 구조**（1단계 결과 반환 후 실행）
- `analyze_trend` 기술 지표 조회
- `get_chip_distribution` 주주 구조 조회

**3단계 · 정보 검색**（앞 두 단계 완료 후 실행）
- `search_stock_news` 최신 뉴스, 주식 매도, 실적 예고 등 리스크 신호 검색

**4단계 · 보고서 생성**（모든 데이터 준비 완료 후, 완전한 의사결정 대시보드 JSON 출력）

> ⚠️ 각 단계의 도구 호출은 결과가 완전히 반환된 후에만 다음 단계로 진행할 수 있습니다. 서로 다른 단계의 도구를 동일한 호출에 병합하는 것은 금지됩니다.

## 핵심 매매 원칙（엄격히 준수 필요）

### 1. 엄격한 진입 전략（고점 추격 금지）
- **절대 고점 추격 금지**：주가가 MA5에서 5% 이상 이탈 시 절대 매수하지 않음
- 이격률 < 2%：최적 매수 구간
- 이격률 2-5%：소규모 진입 가능
- 이격률 > 5%：고점 추격 엄금！직접 "관망"으로 판정

### 2. 추세 매매（추세를 따라）
- **강세 정렬 필수 조건**：MA5 > MA10 > MA20
- 강세 정렬 종목만 매수하고 약세 정렬 종목은 절대 매수 금지
- 이동평균 확산 상승이 이동평균 수렴보다 우선

### 3. 효율 우선（주주 구조）
- 주주 집중도 확인：90% 집중도 < 15% 는 집중을 의미
- 수익 비율 분석：70-90% 수익 구간 시 차익실현 경계 필요
- 평균 매수가와 현재가 관계：현재가가 평균 매수가보다 5-15% 높으면 건강한 상태

### 4. 매수 시점 선호（지지선 재테스트）
- **최적 매수 시점**：거래량 감소 후 MA5 재테스트에서 지지
- **차순위 매수 시점**：MA10 재테스트에서 지지
- **관망 상황**：MA20 하향 이탈 시 관망

### 5. 주요 리스크 점검 항목
- 주식 매도 공시, 실적 적자 예고, 규제 처벌, 업종 정책 악재, 대규모 보호예수 해제

### 6. 밸류에이션 관심（PE/PB）
- PE가 현저히 높을 경우 리스크 포인트에서 설명 필요

### 7. 강세 추세주 완화
- 강세 추세주는 이격률 요건을 적절히 완화할 수 있으며, 소량 추격 매수 시 손절가 설정 필요

## 규칙

1. **도구를 반드시 호출하여 실제 데이터 수집** — 수치를 절대 조작하지 않으며, 모든 데이터는 도구 반환 결과에서 가져와야 합니다.
2. **체계적 분석** — 작업 흐름에 따라 엄격히 단계별로 실행하며, 각 단계 완전 반환 후 다음 단계로 진행하고, 서로 다른 단계의 도구를 동일한 호출에 **병합 금지**.
3. **매매 전략 적용** — 각 활성화된 전략의 조건을 평가하고, 보고서에 전략 판단 결과를 반영합니다.
4. **출력 형식** — 최종 응답은 유효한 의사결정 대시보드 JSON이어야 합니다.
5. **리스크 우선** — 리스크를 반드시 점검해야 합니다（주주 매도, 실적 경고, 규제 문제）.
6. **도구 실패 처리** — 실패 원인을 기록하고, 보유 데이터로 분석을 계속하며, 실패한 도구를 반복 호출하지 않습니다.

{skills_section}

## 출력 형식：의사결정 대시보드 JSON

최종 응답은 아래 구조의 유효한 JSON 객체이어야 합니다：

```json
{{
    "stock_name": "종목 이름",
    "sentiment_score": 0-100 정수,
    "trend_prediction": "강한 상승/상승/횡보/하락/강한 하락",
    "operation_advice": "매수/추가매수/보유/부분매도/매도/관망",
    "decision_type": "buy/hold/sell",
    "confidence_level": "높음/중간/낮음",
    "dashboard": {{
        "core_conclusion": {{
            "one_sentence": "핵심 결론 한 문장（30자 이내）",
            "signal_type": "🟢매수 신호/🟡보유 관망/🔴매도 신호/⚠️리스크 경고",
            "time_sensitivity": "즉시 행동/오늘 내/이번 주 내/급하지 않음",
            "position_advice": {{
                "no_position": "미보유자 조언",
                "has_position": "보유자 조언"
            }}
        }},
        "data_perspective": {{
            "trend_status": {{"ma_alignment": "", "is_bullish": true, "trend_score": 0}},
            "price_position": {{"current_price": 0, "ma5": 0, "ma10": 0, "ma20": 0, "bias_ma5": 0, "bias_status": "", "support_level": 0, "resistance_level": 0}},
            "volume_analysis": {{"volume_ratio": 0, "volume_status": "", "turnover_rate": 0, "volume_meaning": ""}},
            "chip_structure": {{"profit_ratio": 0, "avg_cost": 0, "concentration": 0, "chip_health": ""}}
        }},
        "intelligence": {{
            "latest_news": "",
            "risk_alerts": [],
            "positive_catalysts": [],
            "earnings_outlook": "",
            "sentiment_summary": ""
        }},
        "battle_plan": {{
            "sniper_points": {{"ideal_buy": "", "secondary_buy": "", "stop_loss": "", "take_profit": ""}},
            "position_strategy": {{"suggested_position": "", "entry_plan": "", "risk_control": ""}},
            "action_checklist": []
        }}
    }},
    "analysis_summary": "100자 종합 분석 요약",
    "key_points": "3-5개 핵심 포인트, 쉼표 구분",
    "risk_warning": "리스크 경고",
    "buy_reason": "매매 이유, 매매 원칙 인용",
    "trend_analysis": "추세 패턴 분석",
    "short_term_outlook": "단기 1-3일 전망",
    "medium_term_outlook": "중기 1-2주 전망",
    "technical_analysis": "기술적 종합 분석",
    "ma_analysis": "이동평균 시스템 분석",
    "volume_analysis": "거래량 분석",
    "pattern_analysis": "K선 패턴 분석",
    "fundamental_analysis": "펀더멘털 분석",
    "sector_position": "섹터/업종 분석",
    "company_highlights": "기업 강점/리스크",
    "news_summary": "뉴스 요약",
    "market_sentiment": "시장 심리",
    "hot_topics": "관련 핫토픽"
}}
```

## 평가 기준

### 강한 매수（80-100점）：
- ✅ 강세 정렬：MA5 > MA10 > MA20
- ✅ 낮은 이격률：<2%，최적 매수 시점
- ✅ 거래량 감소 조정 또는 거래량 증가 돌파
- ✅ 주주 구조 집중 건전
- ✅ 뉴스 측면에 긍정적 촉매

### 매수（60-79점）：
- ✅ 강세 정렬 또는 약한 강세
- ✅ 이격률 <5%
- ✅ 거래량 정상
- ⚪ 한 가지 부차적 조건 미충족 허용

### 관망（40-59점）：
- ⚠️ 이격률 >5%（고점 추격 리스크）
- ⚠️ 이동평균 교차로 추세 불명확
- ⚠️ 리스크 이벤트 존재

### 매도/부분매도（0-39점）：
- ❌ 약세 정렬
- ❌ MA20 하향 이탈
- ❌ 거래량 증가 하락
- ❌ 중대 악재

## 의사결정 대시보드 핵심 원칙

1. **핵심 결론 우선**：한 문장으로 매수/매도 여부를 명확히
2. **포지션별 조언 분리**：미보유자와 보유자에게 다른 조언 제공
3. **정확한 매매 시점**：구체적인 가격을 반드시 제시하고 모호한 표현 지양
4. **체크리스트 시각화**：✅⚠️❌ 로 각 점검 결과를 명확히 표시
5. **리스크 우선순위**：뉴스/여론의 리스크 포인트를 눈에 띄게 표시
"""

CHAT_SYSTEM_PROMPT = """당신은 한국 및 미국 주식 추세 매매에 특화된 투자 분석 Agent로, 데이터 도구와 매매 전략을 보유하며 사용자의 주식 투자 질문에 답변할 책임이 있습니다.

## 분석 작업 흐름（단계별로 엄격히 실행하며, 단계 건너뛰기 또는 병합 금지）

사용자가 특정 종목에 대해 질문할 경우, 아래 4단계 순서에 따라 도구를 호출하며, 각 단계의 도구 결과가 모두 반환된 후 다음 단계로 진행합니다：

**1단계 · 시세 및 K선**（반드시 먼저 실행）
- `get_realtime_quote` 호출로 실시간 시세 및 현재가 조회
- `get_daily_history` 호출로 최근 과거 K선 데이터 조회

**2단계 · 기술 지표 및 주주 구조**（1단계 결과 반환 후 실행）
- `analyze_trend` 호출로 MA/MACD/RSI 등 기술 지표 조회
- `get_chip_distribution` 호출로 주주 구조 조회

**3단계 · 정보 검색**（앞 두 단계 완료 후 실행）
- `search_stock_news` 호출로 최신 뉴스 공시, 주식 매도, 실적 예고 등 리스크 신호 검색

**4단계 · 종합 분석**（모든 도구 데이터 준비 완료 후 답변 생성）
- 위 실제 데이터를 기반으로 활성화된 전략과 결합하여 종합 판단 후 투자 의견 출력

> ⚠️ 서로 다른 단계의 도구를 동일한 호출에 병합하는 것은 금지됩니다（예：첫 번째 호출에서 시세, 기술 지표, 뉴스를 동시에 요청하는 것 금지）.

## 핵심 매매 원칙（엄격히 준수 필요）

### 1. 엄격한 진입 전략（고점 추격 금지）
- **절대 고점 추격 금지**：주가가 MA5에서 5% 이상 이탈 시 절대 매수하지 않음
- 이격률 < 2%：최적 매수 구간
- 이격률 2-5%：소규모 진입 가능
- 이격률 > 5%：고점 추격 엄금！직접 "관망"으로 판정

### 2. 추세 매매（추세를 따라）
- **강세 정렬 필수 조건**：MA5 > MA10 > MA20
- 강세 정렬 종목만 매수하고 약세 정렬 종목은 절대 매수 금지
- 이동평균 확산 상승이 이동평균 수렴보다 우선

### 3. 효율 우선（주주 구조）
- 주주 집중도 확인：90% 집중도 < 15% 는 집중을 의미
- 수익 비율 분석：70-90% 수익 구간 시 차익실현 경계 필요
- 평균 매수가와 현재가 관계：현재가가 평균 매수가보다 5-15% 높으면 건강한 상태

### 4. 매수 시점 선호（지지선 재테스트）
- **최적 매수 시점**：거래량 감소 후 MA5 재테스트에서 지지
- **차순위 매수 시점**：MA10 재테스트에서 지지
- **관망 상황**：MA20 하향 이탈 시 관망

### 5. 주요 리스크 점검 항목
- 주식 매도 공시, 실적 적자 예고, 규제 처벌, 업종 정책 악재, 대규모 보호예수 해제

### 6. 밸류에이션 관심（PE/PB）
- PE가 현저히 높을 경우 리스크 포인트에서 설명 필요

### 7. 강세 추세주 완화
- 강세 추세주는 이격률 요건을 적절히 완화할 수 있으며, 소량 추격 매수 시 손절가 설정 필요

## 규칙

1. **도구를 반드시 호출하여 실제 데이터 수집** — 수치를 절대 조작하지 않으며, 모든 데이터는 도구 반환 결과에서 가져와야 합니다.
2. **매매 전략 적용** — 각 활성화된 전략의 조건을 평가하고, 답변에 전략 판단 결과를 반영합니다.
3. **자유 대화** — 사용자의 질문에 따라 자유롭게 답변하며, JSON 출력 불필요.
4. **리스크 우선** — 리스크를 반드시 점검해야 합니다（주주 매도, 실적 경고, 규제 문제）.
5. **도구 실패 처리** — 실패 원인을 기록하고, 보유 데이터로 분석을 계속하며, 실패한 도구를 반복 호출하지 않습니다.

{skills_section}
"""


# ============================================================
# Agent Executor
# ============================================================

class AgentExecutor:
    """ReAct agent loop with tool calling.

    Usage::

        executor = AgentExecutor(tool_registry, llm_adapter)
        result = executor.run("Analyze stock 005930")
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_adapter: LLMToolAdapter,
        skill_instructions: str = "",
        max_steps: int = 10,
    ):
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter
        self.skill_instructions = skill_instructions
        self.max_steps = max_steps

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a given task.

        Args:
            task: The user task / analysis request.
            context: Optional context dict (e.g., {"stock_code": "005930"}).

        Returns:
            AgentResult with parsed dashboard or error.
        """
        start_time = time.time()
        tool_calls_log: List[Dict[str, Any]] = []
        total_tokens = 0

        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## 활성화된 매매 전략\n\n{self.skill_instructions}"
        system_prompt = AGENT_SYSTEM_PROMPT.format(skills_section=skills_section)

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_user_message(task, context)},
        ]

        return self._run_loop(messages, tool_decls, start_time, tool_calls_log, total_tokens, parse_dashboard=True)

    def chat(self, message: str, session_id: str, progress_callback: Optional[Callable] = None, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a free-form chat message.

        Args:
            message: The user's chat message.
            session_id: The conversation session ID.
            progress_callback: Optional callback for streaming progress events.
            context: Optional context dict from previous analysis for data reuse.

        Returns:
            AgentResult with the text response.
        """
        from src.agent.conversation import conversation_manager
        
        start_time = time.time()
        tool_calls_log: List[Dict[str, Any]] = []
        total_tokens = 0

        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## 활성화된 매매 전략\n\n{self.skill_instructions}"
        system_prompt = CHAT_SYSTEM_PROMPT.format(skills_section=skills_section)

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Get conversation history
        session = conversation_manager.get_or_create(session_id)
        history = session.get_history()

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(history)

        # Inject previous analysis context if provided (data reuse from report follow-up)
        if context:
            context_parts = []
            if context.get("stock_code"):
                context_parts.append(f"종목 코드: {context['stock_code']}")
            if context.get("stock_name"):
                context_parts.append(f"종목명: {context['stock_name']}")
            if context.get("previous_price"):
                context_parts.append(f"이전 분석 가격: {context['previous_price']}")
            if context.get("previous_change_pct"):
                context_parts.append(f"이전 등락률: {context['previous_change_pct']}%")
            if context.get("previous_analysis_summary"):
                summary = context["previous_analysis_summary"]
                summary_text = json.dumps(summary, ensure_ascii=False) if isinstance(summary, dict) else str(summary)
                context_parts.append(f"이전 분석 요약:\n{summary_text}")
            if context.get("previous_strategy"):
                strategy = context["previous_strategy"]
                strategy_text = json.dumps(strategy, ensure_ascii=False) if isinstance(strategy, dict) else str(strategy)
                context_parts.append(f"이전 전략 분석:\n{strategy_text}")
            if context_parts:
                context_msg = "[시스템 제공 과거 분석 컨텍스트, 참고 비교 가능]\n" + "\n".join(context_parts)
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "네, 해당 종목의 과거 분석 데이터를 파악했습니다. 궁금하신 점을 말씀해 주세요."})

        messages.append({"role": "user", "content": message})

        # Persist the user turn immediately so the session appears in history during processing
        conversation_manager.add_message(session_id, "user", message)

        result = self._run_loop(messages, tool_decls, start_time, tool_calls_log, total_tokens, parse_dashboard=False, progress_callback=progress_callback)

        # Persist assistant reply (or error note) for context continuity
        if result.success:
            conversation_manager.add_message(session_id, "assistant", result.content)
        else:
            error_note = f"[분석 실패] {result.error or '알 수 없는 오류'}"
            conversation_manager.add_message(session_id, "assistant", error_note)

        return result

    def _run_loop(self, messages: List[Dict[str, Any]], tool_decls: List[Dict[str, Any]], start_time: float, tool_calls_log: List[Dict[str, Any]], total_tokens: int, parse_dashboard: bool, progress_callback: Optional[Callable] = None) -> AgentResult:
        provider_used = ""
        models_used: List[str] = []

        for step in range(self.max_steps):
            logger.info(f"Agent step {step + 1}/{self.max_steps}")

            if progress_callback:
                if not tool_calls_log:
                    thinking_msg = "분석 경로 수립 중..."
                else:
                    last_tool = tool_calls_log[-1].get("tool", "")
                    label = _THINKING_TOOL_LABELS.get(last_tool, last_tool)
                    thinking_msg = f"「{label}」완료, 심층 분석 계속..."
                progress_callback({"type": "thinking", "step": step + 1, "message": thinking_msg})

            response = self.llm_adapter.call_with_tools(messages, tool_decls)
            provider_used = response.provider
            total_tokens += response.usage.get("total_tokens", 0)
            m = getattr(response, "model", "") or response.provider
            if m and m != "error":
                models_used.append(m)

            if response.tool_calls:
                # LLM wants to call tools
                logger.info(f"Agent requesting {len(response.tool_calls)} tool call(s): "
                          f"{[tc.name for tc in response.tool_calls]}")

                # Add assistant message with tool calls to history
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments,
                            **({"thought_signature": tc.thought_signature} if tc.thought_signature is not None else {}),
                        }
                        for tc in response.tool_calls
                    ],
                }
                # Only present for DeepSeek thinking mode; None for all other providers
                if response.reasoning_content is not None:
                    assistant_msg["reasoning_content"] = response.reasoning_content
                messages.append(assistant_msg)

                # Execute tool calls — parallel when multiple, sequential when single
                tool_results: List[Dict[str, Any]] = []

                def _exec_single_tool(tc_item):
                    """Execute one tool and return (tc, result_str, success, duration)."""
                    t0 = time.time()
                    try:
                        res = self.tool_registry.execute(tc_item.name, **tc_item.arguments)
                        res_str = self._serialize_tool_result(res)
                        ok = True
                    except Exception as e:
                        res_str = json.dumps({"error": str(e)})
                        ok = False
                        logger.warning(f"Tool '{tc_item.name}' failed: {e}")
                    dur = time.time() - t0
                    return tc_item, res_str, ok, round(dur, 2)

                if len(response.tool_calls) == 1:
                    # Single tool — run inline (no thread overhead)
                    tc = response.tool_calls[0]
                    if progress_callback:
                        progress_callback({"type": "tool_start", "step": step + 1, "tool": tc.name})
                    _, result_str, success, tool_duration = _exec_single_tool(tc)
                    if progress_callback:
                        progress_callback({"type": "tool_done", "step": step + 1, "tool": tc.name, "success": success, "duration": tool_duration})
                    tool_calls_log.append({
                        "step": step + 1, "tool": tc.name, "arguments": tc.arguments,
                        "success": success, "duration": tool_duration, "result_length": len(result_str),
                    })
                    tool_results.append({"tc": tc, "result_str": result_str})
                else:
                    # Multiple tools — run in parallel threads
                    for tc in response.tool_calls:
                        if progress_callback:
                            progress_callback({"type": "tool_start", "step": step + 1, "tool": tc.name})

                    with ThreadPoolExecutor(max_workers=min(len(response.tool_calls), 5)) as pool:
                        futures = {pool.submit(_exec_single_tool, tc): tc for tc in response.tool_calls}
                        for future in as_completed(futures):
                            tc_item, result_str, success, tool_duration = future.result()
                            if progress_callback:
                                progress_callback({"type": "tool_done", "step": step + 1, "tool": tc_item.name, "success": success, "duration": tool_duration})
                            tool_calls_log.append({
                                "step": step + 1, "tool": tc_item.name, "arguments": tc_item.arguments,
                                "success": success, "duration": tool_duration, "result_length": len(result_str),
                            })
                            tool_results.append({"tc": tc_item, "result_str": result_str})

                # Append tool results to messages (ordered by original tool_calls order)
                tc_order = {tc.id: i for i, tc in enumerate(response.tool_calls)}
                tool_results.sort(key=lambda x: tc_order.get(x["tc"].id, 0))
                for tr in tool_results:
                    messages.append({
                        "role": "tool",
                        "name": tr["tc"].name,
                        "tool_call_id": tr["tc"].id,
                        "content": tr["result_str"],
                    })

            else:
                # LLM returned text — this is the final answer
                logger.info(f"Agent completed in {step + 1} steps "
                          f"({time.time() - start_time:.1f}s, {total_tokens} tokens)")
                if progress_callback:
                    progress_callback({"type": "generating", "step": step + 1, "message": "최종 분석 생성 중..."})

                final_content = response.content or ""
                model_str = ", ".join(list(dict.fromkeys(x for x in models_used if x))) if models_used else ""

                if parse_dashboard:
                    dashboard = self._parse_dashboard(final_content)
                    return AgentResult(
                        success=dashboard is not None,
                        content=final_content,
                        dashboard=dashboard,
                        tool_calls_log=tool_calls_log,
                        total_steps=step + 1,
                        total_tokens=total_tokens,
                        provider=provider_used,
                        model=model_str,
                        error=None if dashboard else "Failed to parse dashboard JSON from agent response",
                    )
                else:
                    if response.provider == "error":
                        return AgentResult(
                            success=False,
                            content="",
                            dashboard=None,
                            tool_calls_log=tool_calls_log,
                            total_steps=step + 1,
                            total_tokens=total_tokens,
                            provider=provider_used,
                            model=model_str,
                            error=final_content,
                        )
                    return AgentResult(
                        success=True,
                        content=final_content,
                        dashboard=None,
                        tool_calls_log=tool_calls_log,
                        total_steps=step + 1,
                        total_tokens=total_tokens,
                        provider=provider_used,
                        model=model_str,
                        error=None,
                    )

        # Max steps exceeded
        logger.warning(f"Agent hit max steps ({self.max_steps})")
        model_str = ", ".join(list(dict.fromkeys(x for x in models_used if x))) if models_used else ""
        return AgentResult(
            success=False,
            content="",
            tool_calls_log=tool_calls_log,
            total_steps=self.max_steps,
            total_tokens=total_tokens,
            provider=provider_used,
            model=model_str,
            error=f"Agent exceeded max steps ({self.max_steps})",
        )

    def _build_user_message(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the initial user message."""
        parts = [task]
        if context:
            if context.get("stock_code"):
                parts.append(f"\n종목 코드: {context['stock_code']}")
            if context.get("report_type"):
                parts.append(f"보고서 유형: {context['report_type']}")

            # Inject existing context data to avoid duplicate lookups.
            if context.get("realtime_quote"):
                parts.append(f"\n[시스템이 조회한 실시간 시세]\n{json.dumps(context['realtime_quote'], ensure_ascii=False)}")
            if context.get("chip_distribution"):
                parts.append(f"\n[시스템이 조회한 주주 구조]\n{json.dumps(context['chip_distribution'], ensure_ascii=False)}")

        parts.append("\n사용 가능한 도구를 이용하여 누락된 데이터（예：과거 K선, 뉴스 등）를 조회하고, 의사결정 대시보드 JSON 형식으로 분석 결과를 출력하세요.")
        return "\n".join(parts)

    def _serialize_tool_result(self, result: Any) -> str:
        """Serialize a tool result to a JSON string for the LLM."""
        if result is None:
            return json.dumps({"result": None})
        if isinstance(result, str):
            return result
        if isinstance(result, (dict, list)):
            try:
                return json.dumps(result, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(result)
        # Dataclass or object with __dict__
        if hasattr(result, '__dict__'):
            try:
                d = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                return json.dumps(d, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(result)
        return str(result)

    def _parse_dashboard(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract and parse the Decision Dashboard JSON from agent response."""
        if not content:
            return None

        # Try to extract JSON from markdown code blocks
        json_blocks = re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if json_blocks:
            for block in json_blocks:
                try:
                    parsed = json.loads(block)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    try:
                        repaired = repair_json(block)
                        parsed = json.loads(repaired)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        continue

        # Try raw JSON parse
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try json_repair
        try:
            repaired = repair_json(content)
            parsed = json.loads(repaired)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Try to find JSON object in text
        brace_start = content.find('{')
        brace_end = content.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            candidate = content[brace_start:brace_end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                try:
                    repaired = repair_json(candidate)
                    parsed = json.loads(repaired)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass

        logger.warning("Failed to parse dashboard JSON from agent response")
        return None

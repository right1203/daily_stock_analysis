# -*- coding: utf-8 -*-
"""
Ask command - analyze a stock using a specific Agent strategy.

Usage:
    /ask 600519                        -> Analyze with default strategy
    /ask 600519 用缠论分析              -> Parse strategy from message
    /ask 600519 chan_theory             -> Specify strategy id directly
"""

import re
import logging
import uuid
from typing import List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from data_provider.base import canonical_stock_code
from src.config import get_config

logger = logging.getLogger(__name__)

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
    # English aliases
    "chan": "chan_theory",
    "wave": "wave_theory",
    "box": "box_oscillation",
    "trend": "bull_trend",
    "golden cross": "ma_golden_cross",
    "breakout": "volume_breakout",
    "bottom": "bottom_volume",
    "leader": "dragon_head",
}


class AskCommand(BotCommand):
    """
    Ask command handler - invoke Agent with a specific strategy to analyze a stock.

    Usage:
        /ask 600519                    -> Analyze with default strategy (bull_trend)
        /ask 600519 用缠论分析          -> Automatically selects chan_theory strategy
        /ask 600519 chan_theory         -> Directly specify strategy id
        /ask hk00700 波浪理论看看       -> HK stock with wave_theory
    """

    @property
    def name(self) -> str:
        return "ask"

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
        """Validate arguments."""
        if not args:
            return "종목코드를 입력하세요. 사용법: /ask <종목코드> [전략명]\n예시: /ask 005930 추세분석"

        code = args[0].upper()
        is_a_stock = re.match(r"^\d{6}$", code)
        is_hk_stock = re.match(r"^HK\d{5}$", code)
        is_us_stock = re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", code)

        if not (is_a_stock or is_hk_stock or is_us_stock):
            return f"无效的股票代码: {code}（A股6位数字 / 港股HK+5位数字 / 美股1-5个字母）"

        return None

    def _parse_strategy(self, args: List[str]) -> str:
        """Parse strategy from arguments, returning strategy id."""
        if len(args) < 2:
            return "bull_trend"

        # Join remaining args as the strategy text
        strategy_text = " ".join(args[1:]).strip()

        # Try direct strategy id match first
        try:
            from src.agent.factory import get_skill_manager
            sm = get_skill_manager()
            available_ids = [s.name for s in sm.list_skills()]
            if strategy_text in available_ids:
                return strategy_text
        except Exception:
            pass

        # Try CN name mapping
        for cn_name, strategy_id in STRATEGY_NAME_MAP.items():
            if cn_name in strategy_text:
                return strategy_id

        # Default
        return "bull_trend"

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the ask command via Agent pipeline."""
        config = get_config()

        if not config.agent_mode:
            return BotResponse.text_response(
                "⚠️ Agent 模式未开启，无法使用问股功能。\n请在配置中设置 `AGENT_MODE=true`。"
            )

        code = canonical_stock_code(args[0])
        strategy_id = self._parse_strategy(args)
        strategy_text = " ".join(args[1:]).strip() if len(args) > 1 else ""

        logger.info(f"[AskCommand] Stock: {code}, Strategy: {strategy_id}, Extra: {strategy_text}")

        try:
            from src.agent.factory import build_agent_executor
            executor = build_agent_executor(config, skills=[strategy_id] if strategy_id else None)

            # Build message
            user_msg = f"请使用 {strategy_id} 策略分析股票 {code}"
            if strategy_text:
                user_msg = f"请分析股票 {code}，{strategy_text}"

            # Each /ask invocation is a self-contained single-shot analysis; isolate
            # sessions per request so that different stocks or retry attempts never
            # bleed context into each other.
            session_id = f"ask_{code}_{uuid.uuid4()}"
            result = executor.chat(message=user_msg, session_id=session_id)

            if result.success:
                # Prepend strategy tag
                strategy_name = strategy_id
                try:
                    from src.agent.factory import get_skill_manager
                    sm2 = get_skill_manager()
                    for s in sm2.list_skills():
                        if s.name == strategy_id:
                            strategy_name = s.display_name
                            break
                except Exception:
                    pass

                header = f"📊 {code} | 策略: {strategy_name}\n{'─' * 30}\n"
                return BotResponse.text_response(header + result.content)
            else:
                return BotResponse.text_response(f"⚠️ 分析失败: {result.error}")

        except Exception as e:
            logger.error(f"Ask command failed: {e}")
            logger.exception("Ask error details:")
            return BotResponse.text_response(f"⚠️ 问股执行出错: {str(e)}")

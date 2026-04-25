# -*- coding: utf-8 -*-
"""
Chat command for free-form conversation with the Agent.
"""

import logging

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from src.config import get_config

logger = logging.getLogger(__name__)

class ChatCommand(BotCommand):
    """
    Chat command handler.
    
    Usage: /chat <message>
    Example: /chat 삼성전자 최근 흐름을 분석해줘
    """
    
    @property
    def name(self) -> str:
        return "chat"
        
    @property
    def description(self) -> str:
        return "AI 어시스턴트와 자유롭게 대화합니다. Agent 모드가 필요합니다."
        
    @property
    def usage(self) -> str:
        return "/chat <질문>"
        
    @property
    def aliases(self) -> list[str]:
        return ["c"]
        
    def execute(self, message: BotMessage, args: list[str]) -> BotResponse:
        """Execute the chat command."""
        config = get_config()
        
        if not config.agent_mode:
            return BotResponse.text_response(
                "⚠️ Agent 모드가 꺼져 있어 대화 기능을 사용할 수 없습니다.\n"
                "설정에서 `AGENT_MODE=true`를 지정하세요."
            )
            
        if not args:
            return BotResponse.text_response(
                "⚠️ 질문을 입력하세요.\n사용법: `/chat <질문>`\n예시: `/chat 삼성전자 최근 흐름을 분석해줘`"
            )
            
        user_message = " ".join(args)
        session_id = f"{message.platform}_{message.user_id}"
        
        try:
            from src.agent.factory import build_agent_executor
            executor = build_agent_executor(config)
            result = executor.chat(message=user_message, session_id=session_id)
            
            if result.success:
                return BotResponse.text_response(result.content)
            else:
                return BotResponse.text_response(f"⚠️ 대화 실패: {result.error}")
                
        except Exception as e:
            logger.error(f"Chat command failed: {e}")
            logger.exception("Chat error details:")
            return BotResponse.text_response(f"⚠️ 대화 실행 중 오류가 발생했습니다: {str(e)}")

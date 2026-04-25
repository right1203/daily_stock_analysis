# -*- coding: utf-8 -*-
"""Configuration field metadata registry.

This module is the single source of truth for configuration UI metadata,
validation hints, and category grouping.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2026-02-09"

_REMOVED_FIELD_PREFIXES = (
    "AKSHARE_",  # kr-us-static-allow: removed-service
    "BAOSTOCK_",  # kr-us-static-allow: removed-service
    "BOCHA_",  # kr-us-static-allow: removed-service
    "DINGTALK_",  # kr-us-static-allow: removed-service
    "EFINANCE_",  # kr-us-static-allow: removed-service
    "FEISHU_",  # kr-us-static-allow: removed-service
    "PUSHPLUS_",  # kr-us-static-allow: removed-service
    "PYTDX_",  # kr-us-static-allow: removed-service
    "SERVERCHAN3_",  # kr-us-static-allow: removed-service
    "TUSHARE_",  # kr-us-static-allow: removed-service
    "WECOM_",  # kr-us-static-allow: removed-service
    "WECHAT_",  # kr-us-static-allow: removed-service
)

_REMOVED_FIELD_KEYS = {
    "ENABLE_CHIP_DISTRIBUTION",
    "ENABLE_EASTMONEY_PATCH",
    "REALTIME_SOURCE_PRIORITY",
    "TUSHARE_TOKEN",  # kr-us-static-allow: removed-service
}

_CATEGORY_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "category": "base",
        "title": "기본 설정",
        "description": "관심 종목과 애플리케이션 기본 설정입니다.",
        "display_order": 10,
    },
    {
        "category": "ai_model",
        "title": "AI 모델",
        "description": "모델 제공자, 모델명, 추론 파라미터 설정입니다.",
        "display_order": 20,
    },
    {
        "category": "data_source",
        "title": "데이터 소스",
        "description": "시장 데이터 제공자 인증 정보와 우선순위 설정입니다.",
        "display_order": 30,
    },
    {
        "category": "notification",
        "title": "알림",
        "description": "봇, 웹훅, 푸시 채널 관련 설정입니다.",
        "display_order": 40,
    },
    {
        "category": "system",
        "title": "시스템",
        "description": "실행 환경과 스케줄 제어 설정입니다.",
        "display_order": 50,
    },
    {
        "category": "agent",
        "title": "에이전트",
        "description": "에이전트 모드와 전략 설정입니다.",
        "display_order": 55,
    },
    {
        "category": "backtest",
        "title": "백테스트",
        "description": "백테스트 엔진 동작과 평가 파라미터 설정입니다.",
        "display_order": 60,
    },
    {
        "category": "uncategorized",
        "title": "미분류",
        "description": "필드 레지스트리에 매핑되지 않은 키입니다.",
        "display_order": 99,
    },
]

_FIELD_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "STOCK_LIST": {
        "title": "관심 종목 목록",
        "description": "쉼표로 구분한 관심 종목 코드입니다.",
        "category": "base",
        "data_type": "array",
        "ui_control": "textarea",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "005930,035720,AAPL",
        "options": [],
        "validation": {"min_items": 1},
        "display_order": 10,
    },
    # ------------------------------------------------------------------
    # AI Model – LiteLLM unified config
    # ------------------------------------------------------------------
    "LITELLM_MODEL": {
        "title": "기본 모델 (LiteLLM)",
        "description": "provider/model 형식의 통합 기본 모델입니다(예: gemini/gemini-3-flash-preview, openai/deepseek-chat, anthropic/claude-3-5-sonnet-20241022). 비워 두면 사용 가능한 API 키를 기준으로 자동 추론합니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 1,
    },
    "LITELLM_FALLBACK_MODELS": {
        "title": "대체 모델 (LiteLLM)",
        "description": "기본 모델 호출이 실패했을 때 순서대로 시도할 대체 모델 목록입니다. 쉼표로 구분합니다(예: anthropic/claude-3-5-sonnet-20241022,openai/gpt-4o-mini). 제공자 간 이중화를 지원합니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 2,
    },
    # ------------------------------------------------------------------
    # AI Model – Multi-channel LLM configuration
    # ------------------------------------------------------------------
    "LITELLM_CONFIG": {
        "title": "LiteLLM 설정 파일",
        "description": "litellm_config.yaml 경로입니다(고급). 채널 설정과 기존 키보다 우선 적용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 3,
    },
    "LLM_CHANNELS": {
        "title": "LLM 채널",
        "description": "쉼표로 구분한 채널명입니다. 위의 채널 편집기에서 관리합니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 4,
    },
    "AIHUBMIX_KEY": {
        "title": "AIHubmix 키",
        "description": "AIHubmix 통합 API 키입니다. 단일 키로 주요 모델을 사용할 수 있으며 VPN이 필요 없습니다. 기본 URL은 aihubmix.com/v1로 자동 설정됩니다. 키 발급: https://aihubmix.com/?aff=CfMq",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 5,
    },
    # ------------------------------------------------------------------
    # AI Model – DeepSeek official (independent from OpenAI-compatible)
    # ------------------------------------------------------------------
    "DEEPSEEK_API_KEY": {
        "title": "DeepSeek API 키",
        "description": "공식 DeepSeek API 키입니다(https://platform.deepseek.com). 이 값만 설정하면 openai/deepseek-chat을 자동 추론합니다. 멀티 채널 모드에서도 사용할 수 있습니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 6,
    },
    "DEEPSEEK_API_KEYS": {
        "title": "DeepSeek API 키 목록",
        "description": "부하 분산에 사용할 DeepSeek API 키 목록입니다. 쉼표로 구분하며 DEEPSEEK_API_KEY보다 우선 적용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 7,
    },
    "ENABLE_REALTIME_TECHNICAL_INDICATORS": {
        "title": "실시간 기술 지표",
        "description": "MA5/MA10/MA20 및 추세 분석에 장중 실시간 가격을 사용합니다(Issue #234). 끄면 전일 종가를 사용합니다.",
        "category": "data_source",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 21,
    },
    "TAVILY_API_KEYS": {
        "title": "Tavily API 키 목록",
        "description": "쉼표로 구분한 Tavily API 키 목록입니다.",
        "category": "data_source",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 30,
    },
    "SERPAPI_API_KEYS": {
        "title": "SerpAPI 키 목록",
        "description": "쉼표로 구분한 SerpAPI 키 목록입니다.",
        "category": "data_source",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 40,
    },
    "BRAVE_API_KEYS": {
        "title": "Brave API 키 목록",
        "description": "쉼표로 구분한 Brave Search API 키 목록입니다.",
        "category": "data_source",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 50,
    },
    "NAVER_API_KEYS": {
        "title": "Naver API 키 목록",
        "description": "client_id:client_secret 형식의 Naver Search 키 쌍을 쉼표로 구분해 입력합니다.",
        "category": "data_source",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 51,
    },
    "ENABLE_REALTIME_QUOTE": {
        "title": "실시간 시세 사용",
        "description": "실시간 시장 시세를 사용합니다. 끄면 과거 종가만 사용합니다.",
        "category": "data_source",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 22,
    },
    "NEWS_MAX_AGE_DAYS": {
        "title": "뉴스 최대 기간(일)",
        "description": "분석에 포함할 뉴스의 최대 기간입니다. 이보다 오래된 기사는 분석 맥락에서 제외됩니다.",
        "category": "data_source",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "3",
        "options": [],
        "validation": {"min": 1, "max": 30},
        "display_order": 60,
    },
    "BIAS_THRESHOLD": {
        "title": "이격도 임계값(%)",
        "description": "MA5 대비 이격도 임계값(%)입니다. 초과하면 추격 매수 경고가 발생합니다. 강한 추세 종목은 자동으로 1.5배까지 완화됩니다.",
        "category": "data_source",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "5.0",
        "options": [],
        "validation": {"min": 0.0, "max": 50.0},
        "display_order": 61,
    },
    "GEMINI_API_KEY": {
        "title": "Gemini API 키",
        "description": "Gemini 서비스용 단일 API 키입니다(https://aistudio.google.com).",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 10,
    },
    "GEMINI_API_KEYS": {
        "title": "Gemini API 키 목록",
        "description": "부하 분산에 사용할 Gemini API 키 목록입니다. 쉼표로 구분하며 GEMINI_API_KEY보다 우선 적용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 11,
    },
    "GEMINI_MODEL": {
        "title": "Gemini 모델",
        "description": "Gemini 모델명입니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "gemini-3-flash-preview",
        "options": [],
        "validation": {},
        "display_order": 20,
    },
    "GEMINI_MODEL_FALLBACK": {
        "title": "Gemini 대체 모델",
        "description": "대체 Gemini 모델명입니다. LITELLM_FALLBACK_MODELS가 없고 기본 모델이 Gemini일 때 사용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "gemini-2.5-flash",
        "options": [],
        "validation": {},
        "display_order": 21,
    },
    "GEMINI_TEMPERATURE": {
        "title": "Gemini 온도",
        "description": "온도 파라미터입니다. 범위는 [0.0, 2.0]입니다.",
        "category": "ai_model",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "0.7",
        "options": [],
        "validation": {"min": 0.0, "max": 2.0},
        "display_order": 30,
    },
    "OPENAI_API_KEY": {
        "title": "OpenAI API 키",
        "description": "OpenAI 호환 서비스용 API 키입니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 40,
    },
    "OPENAI_API_KEYS": {
        "title": "OpenAI API 키 목록",
        "description": "부하 분산에 사용할 OpenAI 호환 API 키 목록입니다. 쉼표로 구분하며 AIHUBMIX_KEY와 OPENAI_API_KEY보다 우선 적용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 41,
    },
    "OPENAI_BASE_URL": {
        "title": "OpenAI 기본 URL",
        "description": "OpenAI 호환 엔드포인트의 기본 URL입니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 50,
    },
    "OPENAI_MODEL": {
        "title": "OpenAI 모델",
        "description": "OpenAI 호환 엔드포인트에서 사용할 모델명입니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "gpt-4o-mini",
        "options": [],
        "validation": {},
        "display_order": 60,
    },
    "OPENAI_VISION_MODEL": {
        "title": "OpenAI 비전 모델",
        "description": "이미지 추출에 사용할 모델입니다. 일부 API(예: DeepSeek)는 비전을 지원하지 않습니다. 비워 두면 OPENAI_MODEL을 사용합니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 61,
    },
    "OPENAI_TEMPERATURE": {
        "title": "OpenAI 온도",
        "description": "OpenAI 호환 모델의 온도 파라미터입니다. 범위는 [0.0, 2.0]입니다.",
        "category": "ai_model",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "0.7",
        "options": [],
        "validation": {"min": 0.0, "max": 2.0},
        "display_order": 62,
    },
    "ANTHROPIC_API_KEY": {
        "title": "Anthropic API 키",
        "description": "Anthropic Claude API 키입니다(https://console.anthropic.com).",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 35,
    },
    "ANTHROPIC_API_KEYS": {
        "title": "Anthropic API 키 목록",
        "description": "부하 분산에 사용할 Anthropic API 키 목록입니다. 쉼표로 구분하며 ANTHROPIC_API_KEY보다 우선 적용됩니다.",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 35,
    },
    "ANTHROPIC_MODEL": {
        "title": "Anthropic 모델",
        "description": "Claude 모델명입니다(예: claude-3-5-sonnet-20241022).",
        "category": "ai_model",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "claude-3-5-sonnet-20241022",
        "options": [],
        "validation": {},
        "display_order": 36,
    },
    "ANTHROPIC_TEMPERATURE": {
        "title": "Anthropic 온도",
        "description": "온도 파라미터입니다. 범위는 [0.0, 1.0]입니다.",
        "category": "ai_model",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "0.7",
        "options": [],
        "validation": {"min": 0.0, "max": 1.0},
        "display_order": 37,
    },
    "ANTHROPIC_MAX_TOKENS": {
        "title": "Anthropic 최대 토큰",
        "description": "Anthropic API 응답의 최대 토큰 수입니다(기본값 8192).",
        "category": "ai_model",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "8192",
        "options": [],
        "validation": {"min": 256, "max": 8192},
        "display_order": 38,
    },
    "CUSTOM_WEBHOOK_URLS": {
        "title": "사용자 지정 웹훅 URL",
        "description": "사용자 지정 알림에 사용할 웹훅 URL 목록입니다. 쉼표로 구분합니다(Discord, Slack 등).",
        "category": "notification",
        "data_type": "array",
        "ui_control": "textarea",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 50,
    },
    "CUSTOM_WEBHOOK_BEARER_TOKEN": {
        "title": "사용자 지정 웹훅 Bearer 토큰",
        "description": "인증이 필요한 사용자 지정 웹훅에 사용할 Bearer 토큰입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 51,
    },
    "WEBHOOK_VERIFY_SSL": {
        "title": "웹훅 SSL 검증",
        "description": "웹훅 요청의 HTTPS 인증서를 검증합니다. 신뢰할 수 있는 내부망의 자체 서명 인증서에서만 false로 설정하세요. 경고: 끄면 중간자 공격을 허용할 수 있으므로 공개 네트워크에서는 사용하지 마세요.",
        "category": "notification",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 52,
    },
    "REPORT_SUMMARY_ONLY": {
        "title": "리포트 요약만 전송",
        "description": "종목별 상세 내용 없이 분석 요약만 푸시합니다. 많은 종목을 추적할 때 빠른 개요 확인에 적합합니다(Issue #262).",
        "category": "notification",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 53,
    },
    # ------------------------------------------------------------------
    # Notification – Telegram
    # ------------------------------------------------------------------
    "TELEGRAM_BOT_TOKEN": {
        "title": "Telegram 봇 토큰",
        "description": "Telegram 봇 토큰입니다(@BotFather에서 발급).",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 15,
    },
    "TELEGRAM_CHAT_ID": {
        "title": "Telegram 채팅 ID",
        "description": "메시지를 보낼 Telegram 채팅 또는 그룹 ID입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 16,
    },
    "TELEGRAM_MESSAGE_THREAD_ID": {
        "title": "Telegram 스레드 ID",
        "description": "그룹 메시지에 사용할 Telegram 주제 또는 스레드 ID입니다(선택 사항).",
        "category": "notification",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 17,
    },
    # ------------------------------------------------------------------
    # Notification – Email
    # ------------------------------------------------------------------
    "EMAIL_SENDER": {
        "title": "이메일 발신자",
        "description": "발신자 이메일 주소입니다. SMTP 호스트는 자동 감지됩니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 25,
    },
    "EMAIL_PASSWORD": {
        "title": "이메일 비밀번호",
        "description": "이메일 비밀번호 또는 앱 전용 인증 코드입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 26,
    },
    "EMAIL_RECEIVERS": {
        "title": "이메일 수신자",
        "description": "쉼표로 구분한 수신자 이메일 주소입니다. 비워 두면 본인에게 전송합니다.",
        "category": "notification",
        "data_type": "array",
        "ui_control": "textarea",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {"multi_value": True, "delimiter": ","},
        "display_order": 27,
    },
    # ------------------------------------------------------------------
    # Notification – Discord
    # ------------------------------------------------------------------
    "DISCORD_WEBHOOK_URL": {
        "title": "Discord 웹훅 URL",
        "description": "채널 알림에 사용할 Discord 웹훅 URL입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 33,
    },
    "DISCORD_BOT_TOKEN": {
        "title": "Discord 봇 토큰",
        "description": "대화형 봇 모드에 사용할 Discord 봇 토큰입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 34,
    },
    "DISCORD_MAIN_CHANNEL_ID": {
        "title": "Discord 채널 ID",
        "description": "메시지를 보낼 Discord 기본 채널 ID입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 35,
    },
    # ------------------------------------------------------------------
    # Notification – Pushover
    # ------------------------------------------------------------------
    "PUSHOVER_USER_KEY": {
        "title": "Pushover 사용자 키",
        "description": "Pushover 사용자 키입니다(https://pushover.net).",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 42,
    },
    "PUSHOVER_API_TOKEN": {
        "title": "Pushover API 토큰",
        "description": "Pushover 애플리케이션 API 토큰입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 43,
    },
    "ASTRBOT_URL": {
        "title": "AstrBot URL",
        "description": "알림에 사용할 AstrBot 웹훅 또는 API 엔드포인트 URL입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 44,
    },
    "ASTRBOT_TOKEN": {
        "title": "AstrBot 토큰",
        "description": "인증된 알림에 사용할 AstrBot 액세스 토큰입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "password",
        "is_sensitive": True,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 45,
    },
    "SINGLE_STOCK_NOTIFY": {
        "title": "종목별 즉시 알림",
        "description": "모든 결과를 묶어 보내지 않고 각 단일 종목 분석 후 즉시 푸시합니다.",
        "category": "notification",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 54,
    },
    "REPORT_TYPE": {
        "title": "리포트 유형",
        "description": "리포트 형식입니다. 'simple'은 간결한 형식, 'full'은 상세 형식입니다.",
        "category": "notification",
        "data_type": "string",
        "ui_control": "select",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "simple",
        "options": ["simple", "full"],
        "validation": {"enum": ["simple", "full"]},
        "display_order": 55,
    },
    "MERGE_EMAIL_NOTIFICATION": {
        "title": "이메일 알림 병합",
        "description": "종목 분석과 시장 리뷰를 하나의 이메일 알림으로 합칩니다.",
        "category": "notification",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 56,
    },
    "SCHEDULE_TIME": {
        "title": "스케줄 시간",
        "description": "일일 실행 시간입니다. HH:MM 형식으로 입력합니다.",
        "category": "system",
        "data_type": "time",
        "ui_control": "time",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "18:00",
        "options": [],
        "validation": {"pattern": r"^([01]\d|2[0-3]):[0-5]\d$"},
        "display_order": 10,
    },
    "HTTP_PROXY": {
        "title": "HTTP 프록시",
        "description": "선택 사항인 HTTP 프록시 엔드포인트입니다.",
        "category": "system",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 20,
    },
    "LOG_LEVEL": {
        "title": "로그 레벨",
        "description": "애플리케이션 로그 레벨입니다.",
        "category": "system",
        "data_type": "string",
        "ui_control": "select",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "validation": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        "display_order": 30,
    },
    "WEBUI_PORT": {
        "title": "Web UI 포트",
        "description": "Web UI 서비스 포트입니다.",
        "category": "system",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "8000",
        "options": [],
        "validation": {"min": 1, "max": 65535},
        "display_order": 40,
    },
    "RUN_IMMEDIATELY": {
        "title": "즉시 실행",
        "description": "시작 시 분석을 즉시 실행할지 여부입니다(비 스케줄 모드).",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 45,
    },
    "SCHEDULE_ENABLED": {
        "title": "스케줄 사용",
        "description": "일일 예약 분석 실행을 사용합니다.",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 8,
    },
    "SCHEDULE_RUN_IMMEDIATELY": {
        "title": "스케줄 시작 시 즉시 실행",
        "description": "스케줄 모드에서 시작 시 분석을 한 번 즉시 실행할지 여부입니다.",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 11,
    },
    "TRADING_DAY_CHECK_ENABLED": {
        "title": "거래일 확인",
        "description": "비거래일에는 분석을 건너뜁니다. 무시하려면 false로 설정하거나 --force-run을 사용하세요.",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 12,
    },
    "MARKET_REVIEW_ENABLED": {
        "title": "시장 리뷰 사용",
        "description": "분석 리포트에 시장 개요와 리뷰를 포함합니다.",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 46,
    },
    "MARKET_REVIEW_REGION": {
        "title": "시장 리뷰 지역",
        "description": "리뷰할 시장 지역입니다. kr(한국 주식), us(미국 주식), both(둘 다) 중에서 선택합니다.",
        "category": "system",
        "data_type": "string",
        "ui_control": "select",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "kr",
        "options": ["kr", "us", "both"],
        "validation": {"enum": ["kr", "us", "both"]},
        "display_order": 47,
    },
    "MAX_WORKERS": {
        "title": "최대 작업자 수",
        "description": "동시에 실행할 수 있는 최대 분석 스레드 수입니다. API 속도 제한을 피하려면 낮게 유지하세요.",
        "category": "system",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "3",
        "options": [],
        "validation": {"min": 1, "max": 20},
        "display_order": 50,
    },
    "ANALYSIS_DELAY": {
        "title": "분석 지연",
        "description": "개별 종목 분석 사이의 지연 시간(초)입니다. API 속도 제한 대응에 사용합니다.",
        "category": "system",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "0",
        "options": [],
        "validation": {"min": 0, "max": 60},
        "display_order": 51,
    },
    "DEBUG": {
        "title": "디버그 모드",
        "description": "상세 로그를 출력하는 디버그 모드를 사용합니다.",
        "category": "system",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 55,
    },
    "BACKTEST_ENABLED": {
        "title": "백테스트 사용",
        "description": "백테스트 사용 여부입니다.",
        "category": "backtest",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "true",
        "options": [],
        "validation": {},
        "display_order": 10,
    },
    "BACKTEST_EVAL_WINDOW_DAYS": {
        "title": "백테스트 평가 기간(일)",
        "description": "백테스트 평가 기간입니다. 거래일 기준입니다.",
        "category": "backtest",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "10",
        "options": [],
        "validation": {"min": 1, "max": 365},
        "display_order": 20,
    },
    "BACKTEST_MIN_AGE_DAYS": {
        "title": "백테스트 최소 경과일",
        "description": "이 기준보다 오래된 분석 기록만 평가합니다.",
        "category": "backtest",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "14",
        "options": [],
        "validation": {"min": 0, "max": 3650},
        "display_order": 30,
    },
    "BACKTEST_ENGINE_VERSION": {
        "title": "백테스트 엔진 버전",
        "description": "백테스트 엔진 버전 라벨입니다.",
        "category": "backtest",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "v1",
        "options": [],
        "validation": {},
        "display_order": 40,
    },
    "BACKTEST_NEUTRAL_BAND_PCT": {
        "title": "백테스트 중립 구간(%)",
        "description": "결과 라벨링에 사용할 중립 수익률 구간(%)입니다.",
        "category": "backtest",
        "data_type": "number",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "2.0",
        "options": [],
        "validation": {"min": 0.0, "max": 100.0},
        "display_order": 50,
    },
    "AGENT_MODE": {
        "title": "에이전트 모드",
        "description": "종목 분석에 ReAct Agent를 사용합니다.",
        "category": "agent",
        "data_type": "boolean",
        "ui_control": "switch",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "false",
        "options": [],
        "validation": {},
        "display_order": 10,
    },
    "AGENT_MAX_STEPS": {
        "title": "에이전트 최대 단계",
        "description": "에이전트가 수행할 수 있는 최대 단계 수입니다.",
        "category": "agent",
        "data_type": "integer",
        "ui_control": "number",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "10",
        "options": [],
        "validation": {"min": 1, "max": 50},
        "display_order": 20,
    },
    "AGENT_SKILLS": {
        "title": "에이전트 스킬",
        "description": "활성화할 에이전트 전략 목록입니다. 쉼표로 구분합니다. 'all'이 아닌 특정 전략으로 설정하면 예약 작업이 자동으로 Agent 파이프라인을 사용합니다.",
        "category": "agent",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "bull_trend,ma_golden_cross,volume_breakout,shrink_pullback",
        "options": [],
        "validation": {},
        "display_order": 30,
    },
    "AGENT_STRATEGY_DIR": {
        "title": "에이전트 전략 디렉터리",
        "description": "에이전트 전략 YAML 파일이 있는 디렉터리입니다.",
        "category": "agent",
        "data_type": "string",
        "ui_control": "text",
        "is_sensitive": False,
        "is_required": False,
        "is_editable": True,
        "default_value": "strategies",
        "options": [],
        "validation": {},
        "display_order": 40,
    },
}


def get_category_definitions() -> List[Dict[str, Any]]:
    """Return deep-copied category metadata."""
    return deepcopy(_CATEGORY_DEFINITIONS)


def get_registered_field_keys() -> List[str]:
    """Return all explicitly registered keys."""
    return list(_FIELD_DEFINITIONS.keys())


def is_removed_field_key(key: str) -> bool:
    """Return whether a key belongs to a removed legacy data or delivery provider."""
    key_upper = key.upper()
    return key_upper in _REMOVED_FIELD_KEYS or key_upper.startswith(_REMOVED_FIELD_PREFIXES)


def get_removed_field_keys() -> List[str]:
    """Return exact removed keys that should be hidden from active config surfaces."""
    return sorted(_REMOVED_FIELD_KEYS)


def get_field_definition(key: str, value_hint: Optional[str] = None) -> Dict[str, Any]:
    """Return field definition for key, including inferred fallback metadata."""
    key_upper = key.upper()
    if key_upper in _FIELD_DEFINITIONS:
        field = deepcopy(_FIELD_DEFINITIONS[key_upper])
        field["key"] = key_upper
        return field

    category = _infer_category(key_upper)
    data_type = _infer_data_type(key_upper, value_hint)
    field = {
        "key": key_upper,
        "title": f"미등록 설정 ({key_upper})",
        "description": "자동 추론된 필드 메타데이터입니다.",
        "category": category,
        "data_type": data_type,
        "ui_control": _infer_ui_control(data_type, key_upper),
        "is_sensitive": _is_sensitive_key(key_upper),
        "is_required": False,
        "is_editable": True,
        "default_value": None,
        "options": [],
        "validation": {},
        "display_order": 9000,
    }
    return field


def build_schema_response() -> Dict[str, Any]:
    """Build schema payload grouped by category."""
    category_map: Dict[str, Dict[str, Any]] = {}
    for category in get_category_definitions():
        category_map[category["category"]] = {**category, "fields": []}

    for key in sorted(_FIELD_DEFINITIONS.keys()):
        field = get_field_definition(key)
        category_map[field["category"]]["fields"].append(field)

    categories = sorted(category_map.values(), key=lambda item: item["display_order"])
    for category in categories:
        category["fields"] = sorted(
            category["fields"],
            key=lambda item: (item.get("display_order", 9999), item["key"]),
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "categories": categories,
    }


def _is_sensitive_key(key: str) -> bool:
    markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    return any(marker in key for marker in markers)


def _infer_category(key: str) -> str:
    if key == "STOCK_LIST":
        return "base"
    if key.startswith("BACKTEST_"):
        return "backtest"
    if key.startswith(("GEMINI_", "OPENAI_", "ANTHROPIC_", "LITELLM_", "AIHUBMIX_", "DEEPSEEK_", "LLM_")):
        return "ai_model"
    if key.endswith("_PRIORITY") or key.startswith(
        (
            "YFINANCE",
            "TAVILY",
            "SERPAPI",
            "BRAVE",
            "NAVER",
            "NEWS_",
            "BIAS_",
        )
    ) or key == "ENABLE_REALTIME_QUOTE":
        return "data_source"
    if key.startswith((
        "TELEGRAM",
        "EMAIL",
        "PUSHOVER",
        "DISCORD",
        "CUSTOM_WEBHOOK",
        "ASTRBOT",
    )) or "WEBHOOK" in key:
        return "notification"
    if key.startswith(("LOG_", "SCHEDULE_", "WEBUI_", "HTTP_", "HTTPS_", "MAX_", "DEBUG", "MARKET_REVIEW_", "TRADING_DAY_", "ANALYSIS_DELAY")):
        return "system"
    return "uncategorized"


def _infer_data_type(key: str, value_hint: Optional[str]) -> str:
    if key.endswith("_TIME"):
        return "time"
    if value_hint is None:
        return "string"

    lowered = value_hint.strip().lower()
    if lowered in {"true", "false"}:
        return "boolean"

    try:
        int(value_hint)
        return "integer"
    except (TypeError, ValueError):
        pass

    try:
        float(value_hint)
        return "number"
    except (TypeError, ValueError):
        pass

    if key in {"STOCK_LIST", "EMAIL_RECEIVERS", "CUSTOM_WEBHOOK_URLS"}:
        return "array"
    return "string"


def _infer_ui_control(data_type: str, key: str) -> str:
    if _is_sensitive_key(key):
        return "password"
    if data_type == "boolean":
        return "switch"
    if data_type in {"integer", "number"}:
        return "number"
    if data_type == "time":
        return "time"
    if data_type == "array":
        return "textarea"
    return "text"

# -*- coding: utf-8 -*-
"""
===================================
Image stock code extraction (Vision LLM)
===================================

Extract stock codes from screenshots or images using a Vision LLM.
Priority: Gemini -> Anthropic -> OpenAI (first available).
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import List, Optional, Tuple

import litellm

from src.config import Config, get_config

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """이 주식 시장 스크린샷 또는 이미지를 분석하세요.
보이는 모든 주식 코드를 추출하세요.

출력 형식: 유효한 JSON 배열 문자열만 반환하고 markdown이나 설명은 포함하지 마세요.
예시:
- 한국 주식(6자리 숫자): 005930, 035720
- 미국 주식(1-5자 영문): AAPL, TSLA, MSFT

출력 예시: ["005930", "035720", "AAPL"]

주식 코드를 찾지 못하면 []를 반환하세요."""

ALLOWED_MIME = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
VISION_API_TIMEOUT = 60  # seconds; avoid long blocks on network/API issues

# Magic bytes for server-side MIME validation (client Content-Type can be forged)
_IMAGE_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # bytes[8:12] must be WEBP, checked separately
}


def _verify_image_magic_bytes(image_bytes: bytes, mime_type: str) -> None:
    """Verify actual file content matches declared MIME type (rejects forged Content-Type)."""
    if len(image_bytes) < 12:
        raise ValueError("이미지 파일이 너무 작거나 손상되었습니다")
    if mime_type not in _IMAGE_SIGNATURES:
        raise ValueError(f"검증할 수 없는 이미지 유형입니다: {mime_type}")
    if mime_type == "image/webp":
        if image_bytes[:4] != b"RIFF" or image_bytes[8:12] != b"WEBP":
            raise ValueError("파일 내용이 선언된 image/webp 유형과 일치하지 않습니다")
        return
    for sig in _IMAGE_SIGNATURES[mime_type]:
        if image_bytes.startswith(sig):
            return
    raise ValueError(f"파일 내용이 선언된 {mime_type} 유형과 일치하지 않습니다")


def _normalize_code(raw: str) -> Optional[str]:
    """Normalize and validate a single stock code. KR: 6 digits; US: 1-5 letters."""
    s = raw.strip().upper()
    if not s:
        return None
    # KR stocks: 6-digit KRX codes.
    if s.isdigit() and len(s) == 6:
        return s
    # US stocks: 1-5 letters, optionally with . (e.g. BRK.B)
    if re.match(r"^[A-Z]{1,5}(\.[A-Z])?$", s):
        return s
    # Strip Korean exchange suffixes when present.
    for suffix in (".KS", ".KQ"):
        if s.endswith(suffix):
            base = s[: -len(suffix)].strip()
            if base.isdigit() and len(base) == 6:
                return base
    return None


def _parse_codes_from_text(text: str) -> List[str]:
    """Parse stock codes from LLM response text."""
    seen: set[str] = set()
    result: List[str] = []

    # Prefer a JSON array when the model follows the prompt.
    cleaned = text.strip()
    for start in ("```json", "```"):
        if start in cleaned:
            idx = cleaned.find(start)
            cleaned = cleaned[idx + len(start) :].strip()
    end_idx = cleaned.rfind("```")
    if end_idx >= 0:
        cleaned = cleaned[:end_idx].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    c = _normalize_code(item)
                    if c and c not in seen:
                        seen.add(c)
                        result.append(c)
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: find 6-digit KR codes and US ticker symbols.
    for m in re.finditer(r"\b([0-9]{6}|[A-Z]{1,5}(\.[A-Z])?)\b", text, re.IGNORECASE):
        c = _normalize_code(m.group(1))
        if c and c not in seen:
            seen.add(c)
            result.append(c)

    return result


def _resolve_vision_model() -> str:
    """Determine the litellm model to use for vision, with gemini-3 downgrade."""
    cfg = get_config()
    # Prefer explicit vision model, then primary litellm model
    model = (cfg.openai_vision_model or cfg.litellm_model or "").strip()
    if not model:
        # Fallback: infer from available keys
        if cfg.gemini_api_keys:
            model = "gemini/gemini-2.0-flash"
        elif cfg.anthropic_api_keys:
            model = f"anthropic/{cfg.anthropic_model or 'claude-3-5-sonnet-20241022'}"
        elif cfg.openai_api_keys:
            model = f"openai/{cfg.openai_model or 'gpt-4o-mini'}"
        else:
            return ""
    # Gemini 3 does not support vision; downgrade to gemini-2.0-flash
    if "gemini-3" in model:
        model = "gemini/gemini-2.0-flash"
    return model


def _get_api_key_for_model(model: str, cfg: Config) -> Optional[str]:
    """Return the first available API key for the given litellm model."""
    if model.startswith("gemini/") or model.startswith("vertex_ai/"):
        keys = [k for k in cfg.gemini_api_keys if k and len(k) >= 8]
    elif model.startswith("anthropic/"):
        keys = [k for k in cfg.anthropic_api_keys if k and len(k) >= 8]
    else:
        keys = [k for k in cfg.openai_api_keys if k and len(k) >= 8]
    return keys[0] if keys else None


def _call_litellm_vision(image_b64: str, mime_type: str) -> str:
    """Extract stock codes from an image using litellm (all providers via OpenAI vision format)."""
    cfg = get_config()
    model = _resolve_vision_model()
    if not model:
        raise ValueError(
            "Vision API가 설정되지 않았습니다. "
            "LITELLM_MODEL 또는 관련 API Key를 설정하세요."
        )

    api_key = _get_api_key_for_model(model, cfg)
    if not api_key:
        raise ValueError(f"No API key found for vision model {model}")

    data_url = f"data:{mime_type};base64,{image_b64}"
    call_kwargs: dict = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 1024,
        "api_key": api_key,
        "timeout": VISION_API_TIMEOUT,
    }
    # Add api_base and custom headers for OpenAI-compatible providers
    if not model.startswith("gemini/") and not model.startswith("anthropic/") and not model.startswith("vertex_ai/"):
        if cfg.openai_base_url:
            call_kwargs["api_base"] = cfg.openai_base_url
        if cfg.openai_base_url and "aihubmix.com" in cfg.openai_base_url:
            call_kwargs["extra_headers"] = {"APP-Code": "GPIJ3886"}

    response = litellm.completion(**call_kwargs)
    if response and response.choices and response.choices[0].message.content:
        return response.choices[0].message.content
    raise ValueError("LiteLLM vision returned empty response")


def extract_stock_codes_from_image(
    image_bytes: bytes,
    mime_type: str,
) -> Tuple[List[str], str]:
    """
    Extract stock codes from an image using a Vision LLM.

    Provider priority is Gemini, Anthropic, then OpenAI using the first
    configured model.

    Args:
        image_bytes: Raw image bytes.
        mime_type: MIME type, such as image/jpeg or image/png.

    Returns:
        Deduplicated stock code list and raw LLM response text.

    Raises:
        ValueError: Raised when the image is invalid, Vision API is not
        configured, or extraction fails.
    """
    mime_type = (mime_type or "image/jpeg").strip().lower().split(";")[0].strip()
    if mime_type not in ALLOWED_MIME:
        raise ValueError(f"지원하지 않는 이미지 유형입니다: {mime_type}. 허용: {list(ALLOWED_MIME)}")

    if not image_bytes:
        raise ValueError("이미지 내용이 비어 있습니다")

    if len(image_bytes) > MAX_SIZE_BYTES:
        raise ValueError(f"Image too large (max {MAX_SIZE_BYTES // (1024 * 1024)}MB)")

    _verify_image_magic_bytes(image_bytes, mime_type)

    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    try:
        raw = _call_litellm_vision(image_b64, mime_type)
        codes = _parse_codes_from_text(raw)
        model = _resolve_vision_model()
        logger.info(
            f"[ImageExtractor] {model} extracted {len(codes)} codes: "
            f"{codes[:10]}{'...' if len(codes) > 10 else ''}"
        )
        return codes, raw
    except Exception as e:
        raise ValueError(
            f"Vision API 호출에 실패했습니다. API Key와 네트워크를 확인하세요: {e}"
        ) from e

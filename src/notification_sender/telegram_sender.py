# -*- coding: utf-8 -*-
"""
Telegram notification sender service.
Responsibilities:
1. Send text messages through the Telegram Bot API.
2. Send image messages through the Telegram Bot API.
"""
import logging
from typing import Optional
import requests
import time
import re

from src.config import Config


logger = logging.getLogger(__name__)


class TelegramSender:
    
    def __init__(self, config: Config):
        """
        Initialize Telegram configuration.

        Args:
            config: Config object.
        """
        self._telegram_config = {
            'bot_token': getattr(config, 'telegram_bot_token', None),
            'chat_id': getattr(config, 'telegram_chat_id', None),
            'message_thread_id': getattr(config, 'telegram_message_thread_id', None),
        }
    
    def _is_telegram_configured(self) -> bool:
        """Return whether Telegram configuration is complete."""
        return bool(self._telegram_config['bot_token'] and self._telegram_config['chat_id'])
   
    def send_to_telegram(self, content: str) -> bool:
        """
        Send a message to a Telegram bot.
        
        Telegram Bot API format:
        POST https://api.telegram.org/bot<token>/sendMessage
        {
            "chat_id": "xxx",
            "text": "message content",
            "parse_mode": "Markdown"
        }
        
        Args:
            content: Message content in Markdown format.
            
        Returns:
            Whether sending succeeded.
        """
        if not self._is_telegram_configured():
            logger.warning("Telegram 설정이 불완전하여 푸시를 건너뜁니다")
            return False
        
        bot_token = self._telegram_config['bot_token']
        chat_id = self._telegram_config['chat_id']
        message_thread_id = self._telegram_config.get('message_thread_id')
        
        try:
            # Telegram API endpoint.
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Telegram messages are limited to 4096 characters.
            max_length = 4096
            
            if len(content) <= max_length:
                # Send a single message.
                return self._send_telegram_message(api_url, chat_id, content, message_thread_id)
            else:
                # Send long messages in chunks.
                return self._send_telegram_chunked(api_url, chat_id, content, max_length, message_thread_id)
                
        except Exception as e:
            logger.error(f"Telegram 메시지 전송 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _send_telegram_message(self, api_url: str, chat_id: str, text: str, message_thread_id: Optional[str] = None) -> bool:
        """Send a single Telegram message with exponential backoff retry (Fixes #287)"""
        # Convert Markdown to Telegram-compatible format
        telegram_text = self._convert_to_telegram_markdown(text)
        
        payload = {
            "chat_id": chat_id,
            "text": telegram_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        if message_thread_id:
            payload['message_thread_id'] = message_thread_id

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(api_url, json=payload, timeout=10)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries:
                    delay = 2 ** attempt  # 2s, 4s
                    logger.warning(f"Telegram request failed (attempt {attempt}/{max_retries}): {e}, "
                                   f"retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Telegram request failed after {max_retries} attempts: {e}")
                    return False
        
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("Telegram 메시지 전송 성공")
                    return True
                else:
                    error_desc = result.get('description', '알 수 없는 오류')
                    logger.error(f"Telegram 오류 응답: {error_desc}")
                    
                    # If Markdown parsing failed, fall back to plain text
                    if 'parse' in error_desc.lower() or 'markdown' in error_desc.lower():
                        logger.info("일반 텍스트 형식으로 다시 전송합니다...")
                        plain_payload = dict(payload)
                        plain_payload.pop('parse_mode', None)
                        plain_payload['text'] = text  # Use original text
                        
                        try:
                            response = requests.post(api_url, json=plain_payload, timeout=10)
                            if response.status_code == 200 and response.json().get('ok'):
                                logger.info("Telegram 메시지 전송 성공(일반 텍스트)")
                                return True
                        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                            logger.error(f"Telegram plain-text fallback failed: {e}")
                    
                    return False
            elif response.status_code == 429:
                # Rate limited — respect Retry-After header
                retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                if attempt < max_retries:
                    logger.warning(f"Telegram rate limited, retrying in {retry_after}s "
                                   f"(attempt {attempt}/{max_retries})...")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(f"Telegram rate limited after {max_retries} attempts")
                    return False
            else:
                if attempt < max_retries and response.status_code >= 500:
                    delay = 2 ** attempt
                    logger.warning(f"Telegram server error HTTP {response.status_code} "
                                   f"(attempt {attempt}/{max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                logger.error(f"Telegram 요청 실패: HTTP {response.status_code}")
                logger.error(f"응답 내용: {response.text}")
                return False

        return False
    
    def _send_telegram_chunked(self, api_url: str, chat_id: str, content: str, max_length: int, message_thread_id: Optional[str] = None) -> bool:
        """Send a long Telegram message in chunks."""
        # Split by paragraph sections.
        sections = content.split("\n---\n")
        
        current_chunk = []
        current_length = 0
        all_success = True
        chunk_index = 1
        
        for section in sections:
            section_length = len(section) + 5  # +5 for "\n---\n"
            
            if current_length + section_length > max_length:
                # Send the current chunk.
                if current_chunk:
                    chunk_content = "\n---\n".join(current_chunk)
                    logger.info(f"Telegram 메시지 조각 {chunk_index} 전송 중...")
                    if not self._send_telegram_message(api_url, chat_id, chunk_content, message_thread_id):
                        all_success = False
                    chunk_index += 1
                
                # Reset chunk state.
                current_chunk = [section]
                current_length = section_length
            else:
                current_chunk.append(section)
                current_length += section_length
        
        # Send the final chunk.
        if current_chunk:
            chunk_content = "\n---\n".join(current_chunk)
            logger.info(f"Telegram 메시지 조각 {chunk_index} 전송 중...")
            if not self._send_telegram_message(api_url, chat_id, chunk_content, message_thread_id):
                all_success = False
                
        return all_success

    def _send_telegram_photo(self, image_bytes: bytes) -> bool:
        """Send image via Telegram sendPhoto API (Issue #289)."""
        if not self._is_telegram_configured():
            return False
        bot_token = self._telegram_config['bot_token']
        chat_id = self._telegram_config['chat_id']
        message_thread_id = self._telegram_config.get('message_thread_id')
        api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        try:
            data = {"chat_id": chat_id}
            if message_thread_id:
                data['message_thread_id'] = message_thread_id
            files = {"photo": ("report.png", image_bytes, "image/png")}
            response = requests.post(api_url, data=data, files=files, timeout=30)
            if response.status_code == 200 and response.json().get('ok'):
                logger.info("Telegram 이미지 전송 성공")
                return True
            logger.error("Telegram 이미지 전송 실패: %s", response.text[:200])
            return False
        except Exception as e:
            logger.error("Telegram 이미지 전송 예외: %s", e)
            return False

    def _convert_to_telegram_markdown(self, text: str) -> str:
        """
        Convert standard Markdown to the subset supported by Telegram.
        
        Telegram Markdown limitations:
        - Heading markers are not supported.
        - Use *bold* instead of **bold**.
        - Use _italic_.
        """
        result = text
        
        # Remove heading markers because Telegram does not support them.
        result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)
        
        # Convert **bold** to *bold*.
        result = re.sub(r'\*\*(.+?)\*\*', r'*\1*', result)
        
        # Escape special characters for Telegram Markdown, but preserve link syntax [text](url)
        # Step 1: temporarily protect markdown links
        import uuid as _uuid
        _link_placeholder = f"__LINK_{_uuid.uuid4().hex[:8]}__"
        _links = []
        def _save_link(m):
            _links.append(m.group(0))
            return f"{_link_placeholder}{len(_links) - 1}"
        result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _save_link, result)

        # Step 2: escape remaining special chars
        for char in ['[', ']', '(', ')']:
            result = result.replace(char, f'\\{char}')

        # Step 3: restore links
        for i, link in enumerate(_links):
            result = result.replace(f"{_link_placeholder}{i}", link)

        return result

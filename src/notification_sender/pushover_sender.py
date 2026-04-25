# -*- coding: utf-8 -*-
"""
Pushover notification sender service.
Responsibilities:
1. Send Pushover messages through the Pushover API.
"""
import logging
from typing import Optional
from datetime import datetime
import requests

from src.config import Config
from src.formatters import markdown_to_plain_text


logger = logging.getLogger(__name__)


class PushoverSender:
    
    def __init__(self, config: Config):
        """
        Initialize Pushover configuration.

        Args:
            config: Config object.
        """
        self._pushover_config = {
            'user_key': getattr(config, 'pushover_user_key', None),
            'api_token': getattr(config, 'pushover_api_token', None),
        }
        
    def _is_pushover_configured(self) -> bool:
        """Return whether Pushover configuration is complete."""
        return bool(self._pushover_config['user_key'] and self._pushover_config['api_token'])

    def send_to_pushover(self, content: str, title: Optional[str] = None) -> bool:
        """
        Send a message to Pushover.
        
        Pushover API format:
        POST https://api.pushover.net/1/messages.json
        {
            "token": "application API token",
            "user": "user key",
            "message": "message content",
            "title": "optional title"
        }
        
        Pushover characteristics:
        - Supports iOS, Android, and desktop push notifications.
        - Messages are limited to 1024 characters.
        - Supports priority settings.
        - Supports HTML formatting.
        
        Args:
            content: Message content in Markdown format, converted to plain text.
            title: Optional message title. Defaults to the stock analysis report title.
            
        Returns:
            Whether sending succeeded.
        """
        if not self._is_pushover_configured():
            logger.warning("Pushover 설정이 불완전하여 푸시를 건너뜁니다")
            return False
        
        user_key = self._pushover_config['user_key']
        api_token = self._pushover_config['api_token']
        
        # Pushover API endpoint.
        api_url = "https://api.pushover.net/1/messages.json"
        
        # Build the default message title.
        if title is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            title = f"📈 주식 분석 보고서 - {date_str}"
        
        # Pushover messages are limited to 1024 characters.
        max_length = 1024
        
        # Convert Markdown to plain text for broad compatibility.
        plain_content = markdown_to_plain_text(content)
        
        if len(plain_content) <= max_length:
            # Send a single message.
            return self._send_pushover_message(api_url, user_key, api_token, plain_content, title)
        else:
            # Send long messages in chunks.
            return self._send_pushover_chunked(api_url, user_key, api_token, plain_content, title, max_length)
      
    def _send_pushover_message(
        self, 
        api_url: str, 
        user_key: str, 
        api_token: str, 
        message: str, 
        title: str,
        priority: int = 0
    ) -> bool:
        """
        Send a single Pushover message.
        
        Args:
            api_url: Pushover API endpoint.
            user_key: User key.
            api_token: Application API token.
            message: Message content.
            title: Message title.
            priority: Priority from -2 to 2. Defaults to 0.
        """
        try:
            payload = {
                "token": api_token,
                "user": user_key,
                "message": message,
                "title": title,
                "priority": priority,
            }
            
            response = requests.post(api_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 1:
                    logger.info("Pushover 메시지 전송 성공")
                    return True
                else:
                    errors = result.get('errors', ['알 수 없는 오류'])
                    logger.error(f"Pushover 오류 응답: {errors}")
                    return False
            else:
                logger.error(f"Pushover 요청 실패: HTTP {response.status_code}")
                logger.debug(f"응답 내용: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Pushover 메시지 전송 실패: {e}")
            return False
    
    def _send_pushover_chunked(
        self, 
        api_url: str, 
        user_key: str, 
        api_token: str, 
        content: str, 
        title: str,
        max_length: int
    ) -> bool:
        """
        Send a long Pushover message in chunks.
        
        Split by sections so each chunk stays within the maximum length.
        """
        import time
        
        # Split by separator lines or double newlines.
        if "────────" in content:
            sections = content.split("────────")
            separator = "────────"
        else:
            sections = content.split("\n\n")
            separator = "\n\n"
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for section in sections:
            # Calculate the actual length after adding this section.
            # join() places separators between elements, not after every element.
            if current_chunk:
                # Existing chunks need the separator plus the new section.
                new_length = current_length + len(separator) + len(section)
            else:
                # The first section does not need a separator.
                new_length = len(section)
            
            if new_length > max_length:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                current_chunk = [section]
                current_length = len(section)
            else:
                current_chunk.append(section)
                current_length = new_length
        
        if current_chunk:
            chunks.append(separator.join(current_chunk))
        
        total_chunks = len(chunks)
        success_count = 0
        
        logger.info(f"Pushover 분할 전송: 총 {total_chunks}개")
        
        for i, chunk in enumerate(chunks):
            # Add page numbering to the title.
            chunk_title = f"{title} ({i+1}/{total_chunks})" if total_chunks > 1 else title
            
            if self._send_pushover_message(api_url, user_key, api_token, chunk, chunk_title):
                success_count += 1
                logger.info(f"Pushover {i+1}/{total_chunks}번째 조각 전송 성공")
            else:
                logger.error(f"Pushover {i+1}/{total_chunks}번째 조각 전송 실패")
            
            # Pause between chunks to avoid rate limits.
            if i < total_chunks - 1:
                time.sleep(1)
        
        return success_count == total_chunks

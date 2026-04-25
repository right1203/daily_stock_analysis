# -*- coding: utf-8 -*-
"""
Discord 알림 전송 서비스

역할:
1. webhook 또는 Discord bot API를 통해 Discord 메시지 전송
"""
import logging
import requests

from src.config import Config
from src.formatters import chunk_content_by_max_words


logger = logging.getLogger(__name__)


class DiscordSender:
    
    def __init__(self, config: Config):
        """
        Discord 설정 초기화

        Args:
            config: 설정 객체
        """
        self._discord_config = {
            'bot_token': getattr(config, 'discord_bot_token', None),
            'channel_id': getattr(config, 'discord_main_channel_id', None),
            'webhook_url': getattr(config, 'discord_webhook_url', None),
        }
        self._discord_max_words = getattr(config, 'discord_max_words', 2000)
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
    
    def _is_discord_configured(self) -> bool:
        """Discord 설정이 완전한지 확인（Bot 또는 Webhook 지원）"""
        # Webhook 또는 완전한 Bot Token+Channel이 설정된 경우 사용 가능으로 간주
        bot_ok = bool(self._discord_config['bot_token'] and self._discord_config['channel_id'])
        webhook_ok = bool(self._discord_config['webhook_url'])
        return bot_ok or webhook_ok
    
    def send_to_discord(self, content: str) -> bool:
        """
        Discord에 메시지 푸시（Webhook 및 Bot API 지원）
        
        Args:
            content: Markdown 형식의 메시지 내용
            
        Returns:
            전송 성공 여부
        """
        # 내용을 분할하여 단일 메시지가 Discord 제한을 초과하지 않도록 방지
        try:
            chunks = chunk_content_by_max_words(content, self._discord_max_words)
        except ValueError as e:
            logger.error(f"Discord 메시지 분할 실패: {e}, 전체 전송 시도.")
            chunks = [content]

        # Webhook 우선 사용（설정 간단, 낮은 권한）
        if self._discord_config['webhook_url']:
            return all(self._send_discord_webhook(chunk) for chunk in chunks)

        # 다음으로 Bot API 사용（높은 권한, channel_id 필요）
        if self._discord_config['bot_token'] and self._discord_config['channel_id']:
            return all(self._send_discord_bot(chunk) for chunk in chunks)

        logger.warning("Discord 설정이 불완전합니다. 푸시를 건너뜁니다")
        return False

  
    def _send_discord_webhook(self, content: str) -> bool:
        """
        Webhook을 사용하여 Discord에 메시지 전송
        
        Discord Webhook은 Markdown 형식을 지원합니다
        
        Args:
            content: Markdown 형식의 메시지 내용
            
        Returns:
            전송 성공 여부
        """
        try:
            payload = {
                'content': content,
                'username': '주식 분석 봇',
                'avatar_url': 'https://picsum.photos/200'
            }
            
            response = requests.post(
                self._discord_config['webhook_url'],
                json=payload,
                timeout=10,
                verify=self._webhook_verify_ssl
            )
            
            if response.status_code in [200, 204]:
                logger.info("Discord Webhook 메시지 전송 성공")
                return True
            else:
                logger.error(f"Discord Webhook 전송 실패: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Discord Webhook 전송 예외: {e}")
            return False
    
    def _send_discord_bot(self, content: str) -> bool:
        """
        Bot API를 사용하여 Discord에 메시지 전송
        
        Args:
            content: Markdown 형식의 메시지 내용
            
        Returns:
            전송 성공 여부
        """
        try:
            headers = {
                'Authorization': f'Bot {self._discord_config["bot_token"]}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'content': content
            }
            
            url = f'https://discord.com/api/v10/channels/{self._discord_config["channel_id"]}/messages'
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("Discord Bot 메시지 전송 성공")
                return True
            else:
                logger.error(f"Discord Bot 전송 실패: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Discord Bot 전송 예외: {e}")
            return False

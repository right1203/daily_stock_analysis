# -*- coding: utf-8 -*-
"""
AstrBot 알림 전송 서비스

역할:
1. Astrbot API를 통해 AstrBot 메시지 전송
"""
import logging
import json
import hmac
import hashlib
import requests

from src.config import Config
from src.formatters import markdown_to_html_document


logger = logging.getLogger(__name__)


class AstrbotSender:
    
    def __init__(self, config: Config):
        """
        AstrBot 설정 초기화

        Args:
            config: 설정 객체
        """
        self._astrbot_config = {
            'astrbot_url': getattr(config, 'astrbot_url', None),
            'astrbot_token': getattr(config, 'astrbot_token', None),
        }
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
        
    def _is_astrbot_configured(self) -> bool:
        """AstrBot 설정이 완전한지 확인（Bot 또는 Webhook 지원）"""
        # URL이 설정된 경우 사용 가능으로 간주
        url_ok = bool(self._astrbot_config['astrbot_url'])
        return url_ok

    def send_to_astrbot(self, content: str) -> bool:
        """
        AstrBot으로 메시지 푸시（어댑터를 통해 지원）

        Args:
            content: Markdown 형식의 메시지 내용

        Returns:
            전송 성공 여부
        """
        if self._astrbot_config['astrbot_url']:
            return self._send_astrbot(content)

        logger.warning("AstrBot 설정이 불완전합니다. 푸시를 건너뜁니다")
        return False


    def _send_astrbot(self, content: str) -> bool:
        import time
        """
        Bot API를 사용하여 AstrBot에 메시지 전송

        Args:
            content: Markdown 형식의 메시지 내용

        Returns:
            전송 성공 여부
        """

        html_content = markdown_to_html_document(content)

        try:
            payload = {
                'content': html_content
            }
            signature =  ""
            timestamp = str(int(time.time()))
            if self._astrbot_config['astrbot_token']:
                """요청 서명 계산"""
                payload_json = json.dumps(payload, sort_keys=True)
                sign_data = f"{timestamp}.{payload_json}".encode('utf-8')
                key = self._astrbot_config['astrbot_token']
                signature = hmac.new(
                    key.encode('utf-8'),
                    sign_data,
                    hashlib.sha256
                ).hexdigest()
            url = self._astrbot_config['astrbot_url']
            response = requests.post(
                url, json=payload, timeout=10,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": signature,
                    "X-Timestamp": timestamp
                },
                verify=self._webhook_verify_ssl
            )

            if response.status_code == 200:
                logger.info("AstrBot 메시지 전송 성공")
                return True
            else:
                logger.error(f"AstrBot 전송 실패: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"AstrBot 전송 예외: {e}")
            return False

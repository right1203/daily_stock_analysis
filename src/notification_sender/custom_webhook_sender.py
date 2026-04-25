# -*- coding: utf-8 -*-
"""
Custom webhook notification sender service.

Responsibilities:
1. Send messages to generic custom webhook endpoints.
"""
import logging
import json
import requests

from src.config import Config


logger = logging.getLogger(__name__)


class CustomWebhookSender:

    def __init__(self, config: Config):
        """
        Initialize custom webhook configuration.

        Args:
            config: Config object.
        """
        self._custom_webhook_urls = getattr(config, 'custom_webhook_urls', []) or []
        self._custom_webhook_bearer_token = getattr(config, 'custom_webhook_bearer_token', None)
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
 
    def send_to_custom(self, content: str) -> bool:
        """
        Send a message to custom webhook endpoints.
        
        Supports generic webhook endpoints that accept POST JSON.
        Default payload format: {"text": "message content", "content": "message content"}
        
        Applicable targets:
        - Discord Webhook
        - Slack Incoming Webhook
        - Self-hosted notification services
        - Other services that support POST JSON
        
        Args:
            content: Message content in Markdown format.
            
        Returns:
            Whether at least one webhook delivery succeeded.
        """
        if not self._custom_webhook_urls:
            logger.warning("커스텀 Webhook이 설정되지 않았습니다. 푸시를 건너뜁니다")
            return False
        
        success_count = 0
        
        for i, url in enumerate(self._custom_webhook_urls):
            try:
                payload = self._build_custom_webhook_payload(url, content)
                if self._post_custom_webhook(url, payload, timeout=30):
                    logger.info(f"커스텀 Webhook {i+1} 푸시 성공")
                    success_count += 1
                else:
                    logger.error(f"커스텀 Webhook {i+1} 푸시 실패")
                    
            except Exception as e:
                logger.error(f"커스텀 Webhook {i+1} 푸시 예외: {e}")
        
        logger.info(f"커스텀 Webhook 푸시 완료: 성공 {success_count}/{len(self._custom_webhook_urls)}")
        return success_count > 0

    
    def _send_custom_webhook_image(
        self, image_bytes: bytes, fallback_content: str = ""
    ) -> bool:
        """Send image to Custom Webhooks; Discord supports file attachment (Issue #289)."""
        if not self._custom_webhook_urls:
            return False
        success_count = 0
        for i, url in enumerate(self._custom_webhook_urls):
            try:
                if self._is_discord_webhook(url):
                    files = {"file": ("report.png", image_bytes, "image/png")}
                    data = {"content": "📈 주식 지능형 분석 보고서"}
                    headers = {"User-Agent": "StockAnalysis/1.0"}
                    if self._custom_webhook_bearer_token:
                        headers["Authorization"] = (
                            f"Bearer {self._custom_webhook_bearer_token}"
                        )
                    response = requests.post(
                        url, data=data, files=files, headers=headers, timeout=30,
                        verify=self._webhook_verify_ssl
                    )
                    if response.status_code in (200, 204):
                        logger.info("커스텀 Webhook %d(Discord 이미지) 푸시 성공", i + 1)
                        success_count += 1
                    else:
                        logger.error(
                            "커스텀 Webhook %d(Discord 이미지) 푸시 실패: HTTP %s",
                            i + 1, response.status_code,
                        )
                else:
                    if fallback_content:
                        payload = self._build_custom_webhook_payload(url, fallback_content)
                        if self._post_custom_webhook(url, payload, timeout=30):
                            logger.info(
                                "커스텀 Webhook %d(이미지 미지원, 텍스트 폴백) 푸시 성공", i + 1
                            )
                            success_count += 1
                    else:
                        logger.warning(
                            "커스텀 Webhook %d 이미지 미지원, 폴백 내용 없음, 건너뜁니다", i + 1
                        )
            except Exception as e:
                logger.error("커스텀 Webhook %d 이미지 푸시 예외: %s", i + 1, e)
        return success_count > 0

    def _post_custom_webhook(self, url: str, payload: dict, timeout: int = 30) -> bool:
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'StockAnalysis/1.0',
        }
        # Support bearer token authentication (#51).
        if self._custom_webhook_bearer_token:
            headers['Authorization'] = f'Bearer {self._custom_webhook_bearer_token}'
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        response = requests.post(url, data=body, headers=headers, timeout=timeout, verify=self._webhook_verify_ssl)
        if response.status_code == 200:
            return True
        logger.error(f"커스텀 Webhook 푸시 실패: HTTP {response.status_code}")
        logger.debug(f"응답 내용: {response.text[:200]}")
        return False
    
    def _build_custom_webhook_payload(self, url: str, content: str) -> dict:
        """
        Build a webhook payload for the target URL.
        
        Auto-detect common services and use their expected format.
        """
        url_lower = url.lower()
        
        # Discord Webhook
        if 'discord.com/api/webhooks' in url_lower or 'discordapp.com/api/webhooks' in url_lower:
            # Discord has a 2000-character limit.
            truncated = content[:1900] + "..." if len(content) > 1900 else content
            return {
                "content": truncated
            }
        
        # Slack Incoming Webhook
        if 'hooks.slack.com' in url_lower:
            return {
                "text": content,
                "mrkdwn": True
            }
        
        # Bark iOS push endpoint.
        if 'api.day.app' in url_lower:
            return {
                "title": "주식 분석 보고서",
                "body": content[:4000],  # Bark limit.
                "group": "stock"
            }
        
        # Generic format compatible with most webhook services.
        return {
            "text": content,
            "content": content,
            "message": content,
            "body": content
        }

    @staticmethod
    def _is_discord_webhook(url: str) -> bool:
        url_lower = (url or "").lower()
        return (
            'discord.com/api/webhooks' in url_lower
            or 'discordapp.com/api/webhooks' in url_lower
        )

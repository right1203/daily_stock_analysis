# -*- coding: utf-8 -*-
"""
커스텀 Webhook 알림 전송 서비스

역할:
1. 커스텀 Webhook 메시지 전송
"""
import logging
import json
import requests

from src.config import Config
from src.formatters import chunk_content_by_max_bytes, slice_at_max_bytes


logger = logging.getLogger(__name__)


class CustomWebhookSender:

    def __init__(self, config: Config):
        """
        커스텀 Webhook 설정 초기화

        Args:
            config: 설정 객체
        """
        self._custom_webhook_urls = getattr(config, 'custom_webhook_urls', []) or []
        self._custom_webhook_bearer_token = getattr(config, 'custom_webhook_bearer_token', None)
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
 
    def send_to_custom(self, content: str) -> bool:
        """
        커스텀 Webhook으로 메시지 푸시
        
        임의의 POST JSON을 수용하는 Webhook 엔드포인트 지원
        기본 전송 형식: {"text": "메시지 내용", "content": "메시지 내용"}
        
        적용 대상:
        - 다이나톡 봇
        - Discord Webhook
        - Slack Incoming Webhook
        - 자체 구축 알림 서비스
        - 기타 POST JSON을 지원하는 서비스
        
        Args:
            content: 메시지 내용（Markdown 형식）
            
        Returns:
            적어도 하나의 Webhook 전송 성공 여부
        """
        if not self._custom_webhook_urls:
            logger.warning("커스텀 Webhook이 설정되지 않았습니다. 푸시를 건너뜁니다")
            return False
        
        success_count = 0
        
        for i, url in enumerate(self._custom_webhook_urls):
            try:
                # 범용 JSON 형식, 대부분의 Webhook과 호환
                # 다이나톡 형식: {"msgtype": "text", "text": {"content": "xxx"}}
                # Slack 형식: {"text": "xxx"}
                # Discord 형식: {"content": "xxx"}
                
                # 다이나톡 봇은 body 바이트 상한（약 20000 bytes）이 있으며, 초과 시 분할 전송 필요
                if self._is_dingtalk_webhook(url):
                    if self._send_dingtalk_chunked(url, content, max_bytes=20000):
                        logger.info(f"커스텀 Webhook {i+1}（다이나톡）푸시 성공")
                        success_count += 1
                    else:
                        logger.error(f"커스텀 Webhook {i+1}（다이나톡）푸시 실패")
                    continue

                # 기타 Webhook: 단일 전송
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
                        logger.info("커스텀 Webhook %d（Discord 이미지）푸시 성공", i + 1)
                        success_count += 1
                    else:
                        logger.error(
                            "커스텀 Webhook %d（Discord 이미지）푸시 실패: HTTP %s",
                            i + 1, response.status_code,
                        )
                else:
                    if fallback_content:
                        payload = self._build_custom_webhook_payload(url, fallback_content)
                        if self._post_custom_webhook(url, payload, timeout=30):
                            logger.info(
                                "커스텀 Webhook %d（이미지 미지원, 텍스트로 폴백）푸시 성공", i + 1
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
        # Bearer Token 인증 지원（#51）
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
    URL에 따라 해당 Webhook payload 구성
        
    일반적인 서비스를 자동 감지하여 해당 형식 사용
        """
        url_lower = url.lower()
        
        # 다이나톡 봇
        if 'dingtalk' in url_lower or 'oapi.dingtalk.com' in url_lower:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": "주식 분석 보고서",
                    "text": content
                }
            }
        
        # Discord Webhook
        if 'discord.com/api/webhooks' in url_lower or 'discordapp.com/api/webhooks' in url_lower:
            # Discord 2000자 제한
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
        
        # Bark（iOS 푸시）
        if 'api.day.app' in url_lower:
            return {
                "title": "주식 분석 보고서",
                "body": content[:4000],  # Bark 限制
                "group": "stock"
            }
        
        # 범용 형식（대부분의 서비스와 호환）
        return {
            "text": content,
            "content": content,
            "message": content,
            "body": content
        }
    
    def _send_dingtalk_chunked(self, url: str, content: str, max_bytes: int = 20000) -> bool:
        import time as _time

        # payload 오버헤드를 위한 공간 예약, body 초과 방지
        budget = max(1000, max_bytes - 1500)
        chunks = chunk_content_by_max_bytes(content, budget)
        if not chunks:
            return False

        total = len(chunks)
        ok = 0

        for idx, chunk in enumerate(chunks):
            marker = f"\n\n📄 *({idx+1}/{total})*" if total > 1 else ""
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "주식 분석 보고서",
                    "text": chunk + marker,
                },
            }

            # 여전히 초과하는 경우（극단적 상황）, 바이트 단위로 강제 잘라내기
            body_bytes = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            if body_bytes > max_bytes:
                hard_budget = max(200, budget - (body_bytes - max_bytes) - 200)
                payload["markdown"]["text"], _ = slice_at_max_bytes(payload["markdown"]["text"], hard_budget)

            if self._post_custom_webhook(url, payload, timeout=30):
                ok += 1
            else:
                logger.error(f"다이나톡 분할 전송 실패: {idx+1}/{total} 번째 배치")

            if idx < total - 1:
                _time.sleep(1)

        return ok == total

    
    @staticmethod
    def _is_dingtalk_webhook(url: str) -> bool:
        url_lower = (url or "").lower()
        return 'dingtalk' in url_lower or 'oapi.dingtalk.com' in url_lower

    @staticmethod
    def _is_discord_webhook(url: str) -> bool:
        url_lower = (url or "").lower()
        return (
            'discord.com/api/webhooks' in url_lower
            or 'discordapp.com/api/webhooks' in url_lower
        )

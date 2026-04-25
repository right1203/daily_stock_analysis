# -*- coding: utf-8 -*-
"""
===================================
Bot platform base adapter
===================================

Defines the abstract base class that each retained bot platform adapter must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from bot.models import BotMessage, BotResponse, WebhookResponse


class BotPlatform(ABC):
    """
    Abstract base class for bot platform adapters.

    Responsibilities:
    1. Verify webhook request signatures.
    2. Parse platform-specific messages into the common model.
    3. Convert common responses into platform-specific webhook responses.

    Example:
        class MyPlatform(BotPlatform):
            @property
            def platform_name(self) -> str:
                return "telegram"

            def verify_request(self, headers, body) -> bool:
                # Verify signature.
                return True

            def parse_message(self, data) -> Optional[BotMessage]:
                # Parse the incoming message.
                return BotMessage(...)

            def format_response(self, response, message) -> WebhookResponse:
                # Format the response.
                return WebhookResponse.success({"text": response.text})
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Platform identifier.

        Used for routing and logging, for example "telegram" or "web".
        """
        pass
    
    @abstractmethod
    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        Verify the request signature.

        Each platform has its own signature verification mechanism.

        Args:
            headers: HTTP request headers.
            body: Raw request body bytes.

        Returns:
            Whether the signature is valid.
        """
        pass
    
    @abstractmethod
    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """
        Parse a platform message into the common format.

        Converts platform-specific message payloads into BotMessage. Return None for
        payloads that do not need command handling, such as verification callbacks.

        Args:
            data: Parsed JSON payload.

        Returns:
            BotMessage, or None when no handling is needed.
        """
        pass
    
    @abstractmethod
    def format_response(
        self, 
        response: BotResponse, 
        message: BotMessage
    ) -> WebhookResponse:
        """
        Convert a common response into the platform response format.

        Args:
            response: Common response object.
            message: Original message object used to locate the reply target.

        Returns:
            WebhookResponse object.
        """
        pass
    
    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """
        Handle platform verification requests.

        Some platforms send a challenge request during webhook setup. Subclasses may
        override this method to return a specific response.

        Args:
            data: Request payload.

        Returns:
            Verification response, or None if this is not a challenge request.
        """
        return None
    
    def handle_webhook(
        self, 
        headers: Dict[str, str], 
        body: bytes,
        data: Dict[str, Any]
    ) -> Tuple[Optional[BotMessage], Optional[WebhookResponse]]:
        """
        Handle a webhook request.

        This is the main entry point that coordinates challenge handling,
        signature verification, and message parsing.

        Args:
            headers: HTTP request headers.
            body: Raw request body bytes.
            data: Parsed JSON payload.

        Returns:
            (BotMessage, WebhookResponse) tuple.
            - Challenge request: (None, challenge_response)
            - Normal message: (message, None)
            - Verification failure or ignored payload: (None, error_response or None)
        """
        # 1. Check whether this is a verification challenge.
        challenge_response = self.handle_challenge(data)
        if challenge_response:
            return None, challenge_response

        # 2. Verify request signature.
        if not self.verify_request(headers, body):
            return None, WebhookResponse.error("Invalid signature", 403)

        # 3. Parse message.
        message = self.parse_message(data)

        return message, None

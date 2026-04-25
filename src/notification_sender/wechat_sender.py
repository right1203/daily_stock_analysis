# -*- coding: utf-8 -*-
"""WeChat sender compatibility shim.

WeChat delivery is out of scope for the KR+US product profile.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)

# Keep the legacy constant to avoid attribute errors in old paths.
WECHAT_IMAGE_MAX_BYTES = 2 * 1024 * 1024


class WechatSender:
    """No-op sender retained for backward compatibility."""

    def __init__(self, config: Any) -> None:  # noqa: D107
        self._removed = True

    def send_to_wechat(self, content: str) -> bool:
        logger.warning("WeChat delivery is not supported in the KR+US build.")
        return False

    def _send_wechat_image(self, image_bytes: bytes) -> bool:
        logger.warning("WeChat image delivery is not supported in the KR+US build.")
        return False

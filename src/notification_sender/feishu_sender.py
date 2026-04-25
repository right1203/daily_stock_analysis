# -*- coding: utf-8 -*-
"""Feishu sender compatibility shim.

Feishu delivery is out of scope for the KR+US product profile.
This module keeps the legacy class name to avoid import-time failures.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class FeishuSender:
    """No-op sender retained for backward compatibility."""

    def __init__(self, config: Any) -> None:  # noqa: D107
        self._removed = True

    def send_to_feishu(self, content: str) -> bool:
        logger.warning("Feishu delivery is not supported in the KR+US build.")
        return False

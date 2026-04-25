# -*- coding: utf-8 -*-
"""ServerChan sender compatibility shim.

ServerChan delivery is out of scope for the KR+US product profile.
"""

import logging
from typing import Any, Optional


logger = logging.getLogger(__name__)


class Serverchan3Sender:
    """No-op sender retained for backward compatibility."""

    def __init__(self, config: Any) -> None:  # noqa: D107
        self._removed = True

    def send_to_serverchan3(self, content: str, title: Optional[str] = None) -> bool:
        logger.warning("ServerChan delivery is not supported in the KR+US build.")
        return False

# -*- coding: utf-8 -*-
"""
===================================
WebUI startup script
===================================

Starts the Web backend service.
Running `python webui.py` starts the Web backend directly.

Equivalent command:
    python main.py --webui-only

Usage:
  python webui.py
  WEBUI_HOST=0.0.0.0 WEBUI_PORT=8000 python webui.py
"""

from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Start the Web service."""
    # Keep compatibility with legacy environment variable names.
    host = os.getenv("WEBUI_HOST", os.getenv("API_HOST", "127.0.0.1"))
    port = int(os.getenv("WEBUI_PORT", os.getenv("API_PORT", "8000")))

    print(f"Web 서비스를 시작합니다: http://{host}:{port}")
    print(f"API 문서: http://{host}:{port}/docs")
    print()

    try:
        import uvicorn
        from src.config import setup_env
        from src.logging_config import setup_logging

        setup_env()
        setup_logging(log_prefix="web_server")

        uvicorn.run(
            "api.app:app",
            host=host,
            port=port,
            log_level="info",
        )
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

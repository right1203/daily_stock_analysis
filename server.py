# -*- coding: utf-8 -*-
"""
===================================
Daily Stock Analysis - FastAPI service entrypoint
===================================

Responsibilities:
1. Provide RESTful API service.
2. Configure CORS support.
3. Expose health check endpoints.
4. Serve frontend static files in production mode.

Startup:
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
    
    Or use main.py:
    python main.py --serve-only      # Start API service only
    python main.py --serve           # Start API service and run analysis
"""

import logging

from src.config import setup_env, get_config
from src.logging_config import setup_logging

# Initialize environment variables and logging.
setup_env()

config = get_config()
level_name = (config.log_level or "INFO").upper()
level = getattr(logging, level_name, logging.INFO)

setup_logging(
    log_prefix="api_server",
    console_level=level,
    extra_quiet_loggers=['uvicorn', 'fastapi'],
)

# Import the application instance from api.app.
from api.app import app  # noqa: E402

# Export app for uvicorn.
__all__ = ['app']


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

# -*- coding: utf-8 -*-
"""Centralized logging setup for console, normal file, and debug file output."""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class RelativePathFormatter(logging.Formatter):
    """Formatter that outputs paths relative to the project root."""

    def __init__(self, fmt=None, datefmt=None, relative_to=None):
        super().__init__(fmt, datefmt)
        self.relative_to = Path(relative_to) if relative_to else Path.cwd()

    def format(self, record):
        # Convert absolute paths to relative paths.
        try:
            record.pathname = str(Path(record.pathname).relative_to(self.relative_to))
        except ValueError:
            # Keep the original path if it cannot be relativized.
            pass
        return super().format(record)



# Third-party loggers that should be quieter by default.
DEFAULT_QUIET_LOGGERS = [
    'urllib3',
    'sqlalchemy',
    'google',
    'httpx',
]


def setup_logging(
    log_prefix: str = "app",
    log_dir: str = "./logs",
    console_level: Optional[int] = None,
    debug: bool = False,
    extra_quiet_loggers: Optional[List[str]] = None,
) -> None:
    """
    Initialize the logging system.

    Configures three output layers:
    1. Console output, controlled by debug or console_level.
    2. Normal log file, INFO level, 10MB rotation, 5 backups.
    3. Debug log file, DEBUG level, 50MB rotation, 3 backups.

    Args:
        log_prefix: Log filename prefix, for example "api_server" -> api_server_20240101.log.
        log_dir: Log directory, default ./logs.
        console_level: Optional console level, takes precedence over debug.
        debug: Whether to enable DEBUG console output.
        extra_quiet_loggers: Additional third-party logger names to quiet.
    """
    # Determine the console log level.
    if console_level is not None:
        level = console_level
    else:
        level = logging.DEBUG if debug else logging.INFO

    # Create the log directory.
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create date-suffixed log file paths.
    today_str = datetime.now().strftime('%Y%m%d')
    log_file = log_path / f"{log_prefix}_{today_str}.log"
    debug_log_file = log_path / f"{log_prefix}_debug_{today_str}.log"

    # Configure the root logger.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Handlers control the effective output level.

    # Clear existing handlers to avoid duplicates.
    if root_logger.handlers:
        root_logger.handlers.clear()
    # Create a relative-path formatter rooted at the project directory.
    project_root = Path.cwd()
    rel_formatter = RelativePathFormatter(
        LOG_FORMAT, LOG_DATE_FORMAT, relative_to=project_root
    )
    # Handler 1: console output.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(rel_formatter)
    root_logger.addHandler(console_handler)

    # Handler 2: normal log file, INFO level, 10MB rotation.
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(rel_formatter)
    root_logger.addHandler(file_handler)

    # Handler 3: debug log file, DEBUG level with all details.
    debug_handler = RotatingFileHandler(
        debug_log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=3,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(rel_formatter)
    root_logger.addHandler(debug_handler)

    # Quiet third-party libraries.
    quiet_loggers = DEFAULT_QUIET_LOGGERS.copy()
    if extra_quiet_loggers:
        quiet_loggers.extend(extra_quiet_loggers)

    for logger_name in quiet_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Log initialized paths using relative paths when possible.
    try:
        rel_log_path = log_path.resolve().relative_to(project_root)
    except ValueError:
        rel_log_path = log_path

    try:
        rel_log_file = log_file.resolve().relative_to(project_root)
    except ValueError:
        rel_log_file = log_file

    try:
        rel_debug_log_file = debug_log_file.resolve().relative_to(project_root)
    except ValueError:
        rel_debug_log_file = debug_log_file

    logging.info("Logging initialized, log directory: %s", rel_log_path)
    logging.info("Normal log file: %s", rel_log_file)
    logging.info("Debug log file: %s", rel_debug_log_file)

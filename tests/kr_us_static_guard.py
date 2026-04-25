# -*- coding: utf-8 -*-
"""Reusable static scanners for KR/US migration residue tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCAN_TARGETS: tuple[str, ...] = (
    ".env.example",
    "README.md",
    "SKILL.md",
    "api",
    "apps/dsa-desktop",
    "apps/dsa-web/src",
    "bot",
    "data_provider",
    "docker",
    "docs",
    "litellm_config.example.yaml",
    "main.py",
    "pyproject.toml",
    "requirements.txt",
    "server.py",
    "setup.cfg",
    "src",
    "strategies",
    "test.sh",
    "test_env.py",
    "tests",
    "webui.py",
)

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILE_NAMES = {"Dockerfile"}
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
SKIP_RELATIVE_PREFIXES = (
    ("docs", "plans"),
    ("docs", "superpowers"),
    ("sources",),
    ("_workspace",),
)
SKIP_RELATIVE_PATHS = {
    ("docs", "CHANGELOG.md"),
    ("apps", "dsa-web", "package-lock.json"),
    ("uv.lock",),
}

HAN_PATTERN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
REMOVED_SERVICE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?i:"
    r"akshare|baostock|bocha|dingtalk|efinance|feishu|pushplus|pytdx|"  # kr-us-static-allow: removed-service
    r"serverchan3|serverchan|tushare|wecom|wechat"  # kr-us-static-allow: removed-service
    r")(?=$|[^A-Za-z0-9]|[A-Z][a-z])",
)
REMOVED_MARKET_PATTERN = re.compile(
    r"(?i:\bcn\b|\bhk\b|A-share|A-shares|HK stock|HK stocks)|"  # kr-us-static-allow: removed-market
    r"\u0041\u80a1|\u6e2f\u80a1|\u4e0a\u8bc1|\u6df1\u8bc1|"
    r"\u521b\u4e1a\u677f|\u79d1\u521b|\u4e1c\u65b9\u8d22\u5bcc|\u6caa|\u6df1|"
    r"\.SH\b|\.SZ\b|\.SS\b|\.HK\b|"  # kr-us-static-allow: removed-market
    r"(?i:\bSH\d{6}\b|\bSZ\d{6}\b|\bHK\d{5}\b)"
)
ALLOW_MARKER = "kr-us-static-allow:"


def scan_repository(root: Path | None = None) -> list[str]:
    """Scan the active repository paths for unapproved KR/US migration residue."""
    base = root or PROJECT_ROOT
    targets = [base / target for target in SCAN_TARGETS]
    return scan_paths(base, targets)


def scan_paths(root: Path, targets: Sequence[Path]) -> list[str]:
    """Scan selected files or directories and return formatted offender lines."""
    offenders: list[str] = []
    for file_path in _iter_text_files(root, targets):
        offenders.extend(_scan_file(root, file_path))
    return offenders


def _iter_text_files(root: Path, targets: Sequence[Path]) -> Iterable[Path]:
    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            if _is_scannable_file(root, target):
                yield target
            continue
        for file_path in target.rglob("*"):
            if file_path.is_file() and _is_scannable_file(root, file_path):
                yield file_path


def _is_scannable_file(root: Path, file_path: Path) -> bool:
    relative = file_path.relative_to(root)
    relative_parts = relative.parts
    if set(relative_parts) & SKIP_PARTS:
        return False
    if relative_parts in SKIP_RELATIVE_PATHS:
        return False
    if any(relative_parts[: len(prefix)] == prefix for prefix in SKIP_RELATIVE_PREFIXES):
        return False
    return file_path.suffix in TEXT_SUFFIXES or file_path.name in TEXT_FILE_NAMES


def _scan_file(root: Path, file_path: Path) -> list[str]:
    relative = file_path.relative_to(root)
    offenders: list[str] = []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return [f"{relative}:1:non-utf8:{exc}"]

    for line_number, line in enumerate(lines, start=1):
        if HAN_PATTERN.search(line):
            offenders.append(_format_offender(relative, line_number, "han-text", line))
        if REMOVED_SERVICE_PATTERN.search(line) and not _line_allows_category(line, "removed-service"):
            offenders.append(_format_offender(relative, line_number, "removed-service", line))
        if REMOVED_MARKET_PATTERN.search(line) and not _line_allows_category(line, "removed-market"):
            offenders.append(_format_offender(relative, line_number, "removed-market", line))
    return offenders


def _line_allows_category(line: str, category: str) -> bool:
    marker_index = line.find(ALLOW_MARKER)
    if marker_index == -1:
        return False
    marker_value = line[marker_index + len(ALLOW_MARKER):]
    return re.search(rf"(?<![A-Za-z0-9-]){re.escape(category)}(?![A-Za-z0-9-])", marker_value) is not None


def _format_offender(relative: Path, line_number: int, category: str, line: str) -> str:
    return f"{relative}:{line_number}:{category}:{line.strip()}"

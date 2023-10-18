"""Logging with automatic secret redaction.

Credentials must never reach log files or stderr. The redacting filter
scans formatted log records for values that look like secrets and masks them.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    pass

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
]


class RedactingFilter(logging.Filter):
    """Mask potential secrets in any log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for attr in ("msg", "message"):
            try:
                value = getattr(record, attr) if attr != "message" else record.getMessage()
            except Exception:  # pragma: no cover - defensive
                continue
            if isinstance(value, str):
                masked = _redact(value)
                if attr == "msg":
                    record.msg = masked
                else:
                    record.message = masked
        return True


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda _m: "***REDACTED***", text)
    return text


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    for handler in logging.root.handlers:
        handler.addFilter(RedactingFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def redact_text(text: str) -> str:
    """Public helper used by API/CLI to scrub secrets before echoing values."""
    return _redact(text)


def mask_secret(value: str) -> str:
    """Mask a credential value, keeping a short prefix for identification."""
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}...***"


# Convenience: read a credential from env without ever logging it.
def env_credential(name: str) -> str:
    return os.environ.get(name, "")

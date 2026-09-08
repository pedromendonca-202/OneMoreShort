"""Structured logging (structlog → JSON lines file + readable console) and persisted pipeline events."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.orm import Session

_SENSITIVE = ("api_key", "token", "secret", "password", "authorization", "client_secret")
_configured = False


def _redact(_logger, _method, event_dict: dict[str, Any]) -> dict[str, Any]:
    for k in list(event_dict):
        if any(s in k.lower() for s in _SENSITIVE):
            event_dict[k] = "***"
    return event_dict


def configure_logging(logs_dir: Path | str = "logs", level: str = "INFO", console: bool = True) -> None:
    global _configured
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    structlog.configure(
        processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fh = logging.FileHandler(logs_dir / "oms.jsonl", encoding="utf-8")
    fh.setFormatter(structlog.stdlib.ProcessorFormatter(processor=structlog.processors.JSONRenderer(), foreign_pre_chain=shared))
    root.addHandler(fh)
    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(structlog.stdlib.ProcessorFormatter(processor=structlog.dev.ConsoleRenderer(colors=False), foreign_pre_chain=shared))
        root.addHandler(ch)
    for noisy in ("httpx", "httpcore", "googleapiclient.discovery_cache", "urllib3", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True


def get_logger(**bind: Any) -> structlog.stdlib.BoundLogger:
    if not _configured:
        configure_logging()
    return structlog.get_logger("oms").bind(**bind)


def record_event(
    session: Session,
    *,
    action: str,
    status: str,
    production_id: str | None = None,
    stage: str | None = None,
    duration_ms: int | None = None,
    error: str | None = None,
    retry_count: int = 0,
    api: str | None = None,
    cost_usd: float | None = None,
    detail: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> None:
    from app.core.models import Event

    row = Event(
        production_id=production_id, stage=stage, action=action, status=status, duration_ms=duration_ms,
        error=(error or None) and str(error)[:4000], retry_count=retry_count, api=api, cost_usd=cost_usd, detail=detail,
    )
    if at is not None:
        row.at = at
    session.add(row)

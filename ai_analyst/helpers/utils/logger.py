"""Structured logger for AI Analyst pipeline.

Every script imports get_logger() and logs with run_id + stem context.
Output: JSON lines to logs/pipeline.log + human-readable to stderr.

Usage:
    from helpers.utils.logger import get_logger
    logger = get_logger(__name__, run_id="abc123", stem="ecommerce_...")
    logger.info("build_start", slide_count=17)
    logger.warning("chart_missing", chart_id="revenue_bar")
    logger.error("schema_invalid", field="headline", reason="too long")
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Base directory — always relative to this file's location
# ---------------------------------------------------------------------------
_BASE = Path(__file__).resolve().parent.parent.parent   # ai_analyst/
_LOG_DIR = _BASE / "logs"


def _ensure_log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


# ---------------------------------------------------------------------------
# JSON formatter — one JSON object per line (structured)
# ---------------------------------------------------------------------------
class _JsonFormatter(logging.Formatter):
    def __init__(self, run_id: str = "", stem: str = ""):
        super().__init__()
        self._run_id = run_id
        self._stem = stem

    def format(self, record: logging.LogRecord) -> str:
        # Base fields always present
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "run_id": self._run_id or getattr(record, "run_id", ""),
            "stem": self._stem or getattr(record, "stem", ""),
            "event": record.getMessage(),
        }
        # Extra fields passed via logger.info("msg", extra={...})
        skip = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in skip and not key.startswith("_"):
                payload[key] = val

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Human-readable formatter for stderr
# ---------------------------------------------------------------------------
class _HumanFormatter(logging.Formatter):
    _COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        color = self._COLORS.get(record.levelname, "")
        reset = self._RESET if color else ""
        run_id = getattr(record, "run_id", "")
        run_tag = f"[{run_id[:8]}] " if run_id else ""
        return f"{ts} {color}{record.levelname:<8}{reset} {run_tag}{record.name} — {record.getMessage()}"


# ---------------------------------------------------------------------------
# Cache to avoid duplicate handlers
# ---------------------------------------------------------------------------
_loggers: dict[str, logging.Logger] = {}


def get_logger(
    name: str,
    *,
    run_id: str = "",
    stem: str = "",
    level: int = logging.INFO,
) -> "PipelineLogger":
    """Return a configured PipelineLogger.

    Args:
        name:    Module name — use __name__ from calling module.
        run_id:  Unique ID for this pipeline execution. Auto-generated if empty.
        stem:    Dataset stem (e.g. 'ecommerce_orders_2025-01-01_to_2026-06-30').
        level:   Log level. Override with LOG_LEVEL env var.
    """
    run_id = run_id or os.environ.get("PIPELINE_RUN_ID", str(uuid.uuid4())[:8])
    stem = stem or os.environ.get("PIPELINE_STEM", "")
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), level)

    cache_key = f"{name}:{run_id}"
    if cache_key in _loggers:
        return _loggers[cache_key]  # type: ignore[return-value]

    logger = logging.getLogger(cache_key)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        # 1. JSON file handler
        log_file = _ensure_log_dir() / "pipeline.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(_JsonFormatter(run_id=run_id, stem=stem))
        fh.setLevel(level)
        logger.addHandler(fh)

        # 2. Human-readable stderr handler
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(_HumanFormatter())
        sh.setLevel(level)
        logger.addHandler(sh)

    # Wrap with PipelineLogger for extra convenience
    wrapped = PipelineLogger(logger, run_id=run_id, stem=stem)
    _loggers[cache_key] = wrapped  # type: ignore[assignment]
    return wrapped


# ---------------------------------------------------------------------------
# Thin wrapper that auto-injects run_id + stem into every record
# ---------------------------------------------------------------------------
class PipelineLogger:
    """Wraps stdlib Logger. Adds run_id/stem to every log record automatically."""

    def __init__(self, logger: logging.Logger, run_id: str, stem: str):
        self._logger = logger
        self.run_id = run_id
        self.stem = stem
        self._extra = {"run_id": run_id, "stem": stem}

    # --- convenience methods ---
    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, extra={**self._extra, **kwargs})

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, extra={**self._extra, **kwargs})

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, extra={**self._extra, **kwargs})

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, extra={**self._extra, **kwargs})

    def critical(self, event: str, **kwargs: Any) -> None:
        self._logger.critical(event, extra={**self._extra, **kwargs})

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(event, extra={**self._extra, **kwargs})


def new_run_id() -> str:
    """Generate a fresh unique run ID (8-char hex)."""
    return uuid.uuid4().hex[:8]

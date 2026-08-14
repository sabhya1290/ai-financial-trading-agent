"""
utils/logger.py — Structured logger used by every module.

Events are written to both the console (colourised) and a daily
rotating log file so you have a full audit trail of every trade.
"""

import logging
import os
import json
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from config.settings import LOG_DIR, LOG_LEVEL


# ── ensure the logs directory exists ──────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)


class JsonFormatter(logging.Formatter):
    """
    Emits each log record as a single-line JSON object.
    This makes it easy to ship logs to ELK / Splunk / CloudWatch later.
    """
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "module":  record.name,
            "message": record.getMessage(),
        }
        # If the caller attached extra structured data, include it.
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """
    Return (or create) a named logger that writes:
      • pretty output to stdout
      • JSON lines to  logs/agent_YYYY-MM-DD.log  (rotates at midnight)
    """
    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # ── console handler ───────────────────────────────────────────────────────
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        fmt   = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(console)

    # ── rotating file handler (JSON) ──────────────────────────────────────────
    # ── rotating file handler (JSON) ──────────────────────────────────────────
    log_path = os.path.join(LOG_DIR, "agent.log")
    file_hdl = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        delay=True        # ← this one line fixes the Windows WinError 32
    )
    file_hdl.setFormatter(JsonFormatter())
    logger.addHandler(file_hdl)

    return logger


def log_event(logger: logging.Logger, event_type: str, **kwargs) -> None:
    """
    Convenience helper that attaches arbitrary keyword args as structured
    metadata to an INFO log entry.

    Usage:
        log_event(logger, "TRADE_EXECUTED",
                  ticker="AAPL", action="BUY", qty=10, price=182.50)
    """
    record = logging.LogRecord(
        name=logger.name, level=logging.INFO,
        pathname="", lineno=0,
        msg=event_type, args=(), exc_info=None,
    )
    record.extra = kwargs
    for handler in logger.handlers:
        handler.emit(record)

"""Logging setup with an optional structured (JSON) formatter."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

#: Extra record attributes promoted into JSON log payloads.
_EXTRA_FIELDS = ("request_id", "method", "path", "status", "duration_ms")


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(log_format: str = "text") -> None:
    """Install a stdout handler with the requested format."""

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

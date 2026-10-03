import logging
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict

from app.config import settings

# Sensitive keys to redact from logs
SENSITIVE_PATTERNS = [
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'token', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'api_key', re.IGNORECASE),
    re.compile(r'authorization', re.IGNORECASE),
    re.compile(r'credentials', re.IGNORECASE),
]


def redact_sensitive_data(data: Any) -> Any:
    """
    Recursively sanitize dictionaries/lists to prevent credential exposure in logs.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(p.search(str(k)) for p in SENSITIVE_PATTERNS):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = redact_sensitive_data(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


class StructuredLogFormatter(logging.Formatter):
    """
    Structured log formatter outputting machine-readable JSON logs for production observability.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured extras if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "client_ip"):
            log_obj["client_ip"] = record.client_ip

        if record.exc_info and settings.DEBUG:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(redact_sensitive_data(log_obj))


def setup_logging():
    """
    Initialize application logging using configured log level and structured format.
    """
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logger = logging.getLogger("vetra")
    logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()

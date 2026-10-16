"""Structured logging with secret redaction."""

import json
import logging
import re
import sys

_REDACT_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)(['\"]?)([^'\"\s,}]+)(\2)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:=]\s*)(['\"]?)([^'\"\s,}]+)(\2)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([A-Za-z0-9._~+/-]+)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*)(['\"]?)([^'\"\s,}]+)(\2)", re.IGNORECASE),
]

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def redact(text: str) -> str:
    out = text
    for pat in _REDACT_PATTERNS:
        out = pat.sub(lambda m: m.group(1) + "***REDACTED***", out)
    return out


def redact_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return "***@" + domain
    return local[0] + "***" + local[-1] + "@" + domain


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


log = get_logger("pamtengo")

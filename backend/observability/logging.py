from __future__ import annotations

import contextvars
import logging
from typing import Any

from opentelemetry import trace
from pythonjsonlogger.json import JsonFormatter

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

SENSITIVE_WORDS = ("password", "secret", "token", "api_key", "private_key", "authorization", "credential")


def set_request_id(request_id: str | None) -> None:
    request_id_var.set(request_id)


def get_request_id() -> str | None:
    return request_id_var.get()


class SafeJsonFormatter(JsonFormatter):
    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = log_record.pop("asctime", None)
        log_record["service"] = "northbound-control-tower-backend"
        log_record["environment"] = getattr(record, "environment", None) or "development"
        log_record["logger"] = record.name
        log_record["request_id"] = getattr(record, "request_id", None) or get_request_id()
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            log_record["trace_id"] = f"{span_context.trace_id:032x}"
            log_record["span_id"] = f"{span_context.span_id:016x}"
        else:
            log_record["trace_id"] = None
            log_record["span_id"] = None
        self._redact(log_record)

    def _redact(self, payload: dict[str, Any]) -> None:
        for key, value in list(payload.items()):
            lowered = str(key).lower()
            if any(word in lowered for word in SENSITIVE_WORDS):
                payload[key] = "[redacted]"
            elif isinstance(value, str) and any(marker in value for marker in ("Bearer ", "-----BEGIN", "AKIA", "ASIA")):
                payload[key] = "[redacted]"

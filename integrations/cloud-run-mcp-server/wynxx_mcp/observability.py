"""Observability helpers: structured logging and optional OpenTelemetry.

OpenTelemetry is an *optional* dependency. When ``WYNXX_ENABLE_OTEL=true`` and
the OTel packages are installed, tool calls are wrapped in spans and the real
trace id is used in the execution record. Otherwise a correlation id stands in,
so the execution record is always populated.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from .config import Settings

_LOGGER_NAME = "wynxx_mcp"


class _StructuredFormatter(logging.Formatter):
    """Render each log line as a single Cloud Logging-friendly JSON object.

    Cloud Run promotes a stdout line to ``jsonPayload`` (and reads ``severity``)
    only when the *entire* line is one JSON object — any prefix forces it to
    ``textPayload``. So the whole record, including the structured execution
    fields passed via ``extra={"json_fields": ...}``, is serialised here.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        fields = getattr(record, "json_fields", None)
        if fields:
            payload.update(fields)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure structured JSON stdout logging (ingested by Cloud Logging)."""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------

_tracer = None


def init_tracing(settings: Settings) -> None:
    """Initialise OpenTelemetry if enabled and available (best-effort)."""
    global _tracer
    if not settings.enable_otel:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        get_logger().warning(
            "WYNXX_ENABLE_OTEL=true but OpenTelemetry is not installed; "
            "install requirements-otel.txt. Falling back to correlation ids."
        )
        return

    resource = Resource.create({"service.name": settings.mcp_server_id})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(_LOGGER_NAME)
    get_logger().info("OpenTelemetry tracing enabled for %s", settings.mcp_server_id)


@contextmanager
def start_span(name: str) -> Iterator[str]:
    """Yield a trace id, opening an OTel span when tracing is active.

    Always yields a usable id so execution records are never missing a
    ``trace_id`` — even when OpenTelemetry is disabled.
    """
    if _tracer is None:
        yield f"corr-{uuid.uuid4().hex}"
        return

    from opentelemetry import trace  # local import; only when active

    with _tracer.start_as_current_span(name) as span:
        ctx = span.get_span_context()
        # Format as the W3C trace-id hex string when available.
        trace_id = trace.format_trace_id(ctx.trace_id) if ctx and ctx.trace_id else uuid.uuid4().hex
        yield trace_id


def log_execution_record(record: dict) -> None:
    """Emit the execution record as one structured Cloud Logging line.

    The record fields are merged top-level into the JSON line (via
    ``json_fields``), so each becomes a queryable ``jsonPayload`` field in
    Cloud Logging rather than an opaque string.
    """
    get_logger().info("tool execution", extra={"json_fields": record})

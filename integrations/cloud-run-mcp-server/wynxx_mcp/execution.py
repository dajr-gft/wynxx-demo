"""Tool execution instrumentation.

A single context manager, :func:`tool_execution`, wraps every tool call so the
five governance behaviours from the article happen consistently and in one
place: a trace span, timing, status tracking, the embedded
:class:`ExecutionMetadata`, and a structured audit log line.

Usage::

    with tool_execution("analyze_repository") as ctx:
        domain = backend.invoke("analyze_repository", payload)
        return RepositoryAnalysis(**domain, metadata=ctx.metadata())
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from .config import get_settings
from .observability import log_execution_record, start_span
from .schemas import ExecutionMetadata, ExecutionStatus, ModelArmorVerdict


class ExecutionContext:
    """Carries timing and identity for a single tool invocation."""

    def __init__(self, tool: str, trace_id: str) -> None:
        settings = get_settings()
        self.tool = tool
        self.qualified_tool = f"{settings.server_name}.{tool}"
        self.mcp_server = settings.mcp_server_id
        self.backend_mode = settings.mode.value
        self.execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        self.trace_id = trace_id
        self.status = ExecutionStatus.SUCCESS
        self.model_armor_verdict = ModelArmorVerdict.NOT_EVALUATED
        self._start = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)

    def metadata(self) -> ExecutionMetadata:
        """Build the metadata block embedded in the tool response."""
        return ExecutionMetadata(
            execution_id=self.execution_id,
            tool=self.qualified_tool,
            mcp_server=self.mcp_server,
            backend_mode=self.backend_mode,
            status=self.status,
            duration_ms=self.duration_ms,
            model_armor_verdict=self.model_armor_verdict,
            trace_id=self.trace_id,
            timestamp=datetime.now(UTC),
        )


class tool_execution:  # noqa: N801 — used as a context manager, lower-case by convention
    """Context manager that traces, times, and audits a tool invocation."""

    def __init__(self, tool: str) -> None:
        self._tool = tool
        self._span = None
        self.ctx: ExecutionContext | None = None

    def __enter__(self) -> ExecutionContext:
        self._span = start_span(f"tool.{self._tool}")
        trace_id = self._span.__enter__()
        self.ctx = ExecutionContext(self._tool, trace_id)
        return self.ctx

    def __exit__(self, exc_type, exc, tb) -> bool:
        assert self.ctx is not None
        if exc_type is not None:
            self.ctx.status = ExecutionStatus.FAILED
        # Emit the audit record regardless of success/failure.
        log_execution_record(self.ctx.metadata().model_dump(mode="json"))
        if self._span is not None:
            self._span.__exit__(exc_type, exc, tb)
        return False  # never suppress exceptions

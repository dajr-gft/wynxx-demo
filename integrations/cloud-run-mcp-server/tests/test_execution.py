"""Tests for execution instrumentation and metadata."""

from __future__ import annotations

import pytest

from wynxx_mcp.execution import tool_execution
from wynxx_mcp.schemas import ExecutionStatus, ModelArmorVerdict


def test_metadata_is_populated_on_success():
    with tool_execution("analyze_repository") as ctx:
        meta = ctx.metadata()
    assert meta.execution_id.startswith("exec-")
    assert meta.tool == "wynxx.analyze_repository"
    assert meta.mcp_server == "wynxx-sdlc"
    assert meta.backend_mode == "stub"
    assert meta.status is ExecutionStatus.SUCCESS
    assert meta.duration_ms >= 0
    assert meta.trace_id
    assert meta.model_armor_verdict is ModelArmorVerdict.NOT_EVALUATED


def test_status_flips_to_failed_on_exception():
    captured = {}

    with pytest.raises(RuntimeError), tool_execution("generate_tests") as ctx:
        captured["ctx"] = ctx
        raise RuntimeError("boom")

    # The context manager must not swallow the exception, and must have marked
    # the execution as failed before emitting the audit record.
    assert captured["ctx"].status is ExecutionStatus.FAILED

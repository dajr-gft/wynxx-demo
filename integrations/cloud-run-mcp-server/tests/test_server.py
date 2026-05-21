"""Tests for server assembly and the tool bodies end-to-end."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from wynxx_mcp import schemas
from wynxx_mcp.backend import StubBackend
from wynxx_mcp.server import build_server
from wynxx_mcp.toolsets import register_advisory, register_read_only

EXPECTED_TOOLS = {
    "analyze_repository",
    "explain_code",
    "generate_documentation_draft",
    "modernization_assessment",
    "generate_tests",
    "review_code",
}


class CapturingMCP:
    """Minimal stand-in that records the functions registered via @tool.

    Lets us invoke the real tool bodies (backend call + schema + metadata)
    without depending on a specific FastMCP call_tool signature.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(self, *args: Any, **kwargs: Any):
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def test_build_server_registers_all_six_tools():
    server = build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names >= EXPECTED_TOOLS


def test_analyze_repository_returns_structured_result_with_metadata():
    mcp = CapturingMCP()
    register_read_only(mcp, StubBackend())

    result = mcp.tools["analyze_repository"]("payments-service", language="java", depth="deep")

    assert isinstance(result, schemas.RepositoryAnalysis)
    assert result.repository_path == "payments-service"
    assert result.language == "java"
    assert result.findings  # populated
    assert result.metadata.tool == "wynxx.analyze_repository"
    assert result.metadata.trace_id
    # A high-severity risk is surfaced by the stub assessment.
    assert any(r.severity is schemas.Severity.HIGH for r in result.risks)


def test_generate_tests_marks_drafts_with_warnings():
    mcp = CapturingMCP()
    register_advisory(mcp, StubBackend())

    result = mcp.tools["generate_tests"]("payments-service", coverage_target=90)

    assert isinstance(result, schemas.TestGenerationResult)
    assert result.coverage_target == 90
    assert result.generated_files
    assert any("review" in w.lower() for w in result.warnings)

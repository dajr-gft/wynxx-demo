"""Tests for the stub backend and backend selection."""

from __future__ import annotations

import pytest

from wynxx_mcp.backend import BackendError, StubBackend, build_backend
from wynxx_mcp.config import get_settings

ALL_TOOLS = [
    "analyze_repository",
    "explain_code",
    "generate_documentation_draft",
    "modernization_assessment",
    "generate_tests",
    "review_code",
]


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_stub_backend_returns_payload_for_every_tool(tool: str):
    backend = StubBackend()
    result = backend.invoke(tool, {"repository_path": "payments-service", "file_path": "X.java"})
    assert isinstance(result, dict)
    assert result  # non-empty


def test_stub_backend_rejects_unknown_tool():
    with pytest.raises(BackendError):
        StubBackend().invoke("delete_everything", {})


def test_build_backend_defaults_to_stub():
    backend = build_backend(get_settings())
    assert isinstance(backend, StubBackend)


def test_real_mode_requires_backend_url(monkeypatch: pytest.MonkeyPatch):
    import wynxx_mcp.config as config

    monkeypatch.setenv("WYNXX_MODE", "real")
    monkeypatch.delenv("WYNXX_BACKEND_URL", raising=False)
    config._settings = None
    with pytest.raises(ValueError, match="WYNXX_BACKEND_URL"):
        build_backend(get_settings())

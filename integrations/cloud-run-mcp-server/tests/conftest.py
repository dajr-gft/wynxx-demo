"""Shared pytest fixtures.

The settings singleton is cached, so any test that manipulates environment
variables must reset it. The autouse ``stub_mode`` fixture guarantees every
test starts from a clean, offline configuration.
"""

from __future__ import annotations

import pytest

import wynxx_mcp.config as config


def _reset_settings() -> None:
    config._settings = None


@pytest.fixture(autouse=True)
def stub_mode(monkeypatch: pytest.MonkeyPatch):
    """Force offline stub mode with a deterministic configuration."""
    monkeypatch.setenv("WYNXX_MODE", "stub")
    monkeypatch.setenv("WYNXX_SERVER_NAME", "wynxx")
    monkeypatch.setenv("WYNXX_MCP_SERVER_ID", "wynxx-sdlc")
    monkeypatch.setenv("WYNXX_ENABLE_OTEL", "false")
    _reset_settings()
    yield
    _reset_settings()

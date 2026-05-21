"""Runtime configuration for the Wynxx MCP server.

Configuration is read from environment variables (and an optional ``.env``
file) with the ``WYNXX_`` prefix. The single most important switch is
``WYNXX_MODE``, which selects between the offline ``stub`` backend and a live
``real`` backend — the contract never changes silently between the two.
"""

from __future__ import annotations

import os
from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendMode(StrEnum):
    """How the server fulfils tool calls."""

    STUB = "stub"
    REAL = "real"


class Settings(BaseSettings):
    """Process-wide settings, loaded once at startup."""

    model_config = SettingsConfigDict(
        env_prefix="WYNXX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Backend ---------------------------------------------------------
    mode: BackendMode = Field(
        default=BackendMode.STUB,
        description="stub = offline reference responses; real = live Wynxx backend.",
    )
    backend_url: str | None = Field(
        default=None,
        description="Base URL of the live Wynxx backend (required when mode=real).",
    )
    backend_token: str | None = Field(
        default=None,
        description="Optional bearer/ID token forwarded to the live backend.",
    )
    backend_timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)

    # --- Identity --------------------------------------------------------
    server_name: str = Field(default="wynxx", description="MCP server display name.")
    mcp_server_id: str = Field(
        default="wynxx-sdlc",
        description="Logical id used in audit records and Agent Registry.",
    )

    # --- Network ---------------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Bind host.")
    # Cloud Run injects PORT; honour it, falling back to 8080.
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8080")), ge=1, le=65535)

    # --- Observability ---------------------------------------------------
    log_level: str = Field(default="INFO")
    enable_otel: bool = Field(default=False)

    def require_real_backend(self) -> str:
        """Return the backend URL, raising if real mode is misconfigured."""
        if self.mode is BackendMode.REAL and not self.backend_url:
            raise ValueError(
                "WYNXX_MODE=real requires WYNXX_BACKEND_URL to be set "
                "(e.g. https://34.71.69.43.nip.io)."
            )
        return self.backend_url or ""


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
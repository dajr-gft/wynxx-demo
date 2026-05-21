# Copyright 2026 GFT Technologies SE.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for the ADK 2.0 SDLC orchestration workflow."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunMode(StrEnum):
    """How agents fulfil their work."""

    STUB = "stub"  # offline, deterministic — no models, no MCP server required
    REAL = "real"  # real ADK agents calling the Wynxx MCP server via McpToolset


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SDLC_", env_file=".env", extra="ignore")

    mode: RunMode = Field(default=RunMode.STUB)

    # Wynxx MCP server endpoint (used in real mode).
    mcp_url: str = Field(default="https://wynxx-mcp-server-xxxxx.run.app/mcp")

    # Different models for different roles (article: Pro for reasoning, Flash for volume).
    model_pro: str = Field(default="gemini-3-pro")
    model_flash: str = Field(default="gemini-3-flash")

    # Note: Vertex AI / Agent Engine deploy settings come from the standard
    # GOOGLE_CLOUD_* environment variables (see deployment/deploy.py).


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config

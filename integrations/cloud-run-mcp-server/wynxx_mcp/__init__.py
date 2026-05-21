"""Wynxx MCP server — reference implementation (Path A, Cloud Run).

Exposes a Wynxx-style enterprise SDLC platform as Model Context Protocol tools,
split into a read-only toolset and an advisory toolset.
"""

from .server import build_server

__all__ = ["build_server"]
__version__ = "1.0.0"

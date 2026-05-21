"""Wynxx MCP server — assembly and entrypoint.

``build_server`` wires the selected backend into a FastMCP instance and
registers both toolsets. ``main`` runs it over the streamable-HTTP transport,
which exposes the MCP endpoint at ``/mcp`` — the path Agent Gateway and the
consumer surfaces connect to.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .backend import build_backend
from .config import Settings, get_settings
from .observability import configure_logging, get_logger, init_tracing
from .toolsets import register_advisory, register_read_only


def build_server(settings: Settings | None = None) -> FastMCP:
    """Construct a fully-wired FastMCP server (backend + both toolsets)."""
    settings = settings or get_settings()
    configure_logging(settings)
    init_tracing(settings)

    # `stateless_http=True` makes every request self-contained — no per-session
    # server state — which is what Cloud Run autoscaling needs (no instance
    # affinity). Combined with `json_response=True`, each tool call is a plain
    # request/response, ideal for a serverless MCP endpoint behind Agent Gateway.
    mcp = FastMCP(
        settings.server_name,
        json_response=True,
        stateless_http=True,
        host=settings.host,
        port=settings.port,
    )

    backend = build_backend(settings)
    register_read_only(mcp, backend)
    register_advisory(mcp, backend)

    get_logger().info(
        "Wynxx MCP server ready: id=%s mode=%s tools=6 (read-only + advisory)",
        settings.mcp_server_id,
        settings.mode.value,
    )
    return mcp


def main() -> None:
    """Console entrypoint: run the server over streamable HTTP."""
    server = build_server()
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()

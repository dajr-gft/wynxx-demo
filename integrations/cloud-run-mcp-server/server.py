"""Container / Cloud Run entrypoint for the Wynxx MCP server.

This is the file the article's snippet refers to as ``server.py`` and the file
the Dockerfile runs (``CMD ["python", "server.py"]``). The implementation lives
in the :mod:`wynxx_mcp` package so it can be tested and reused; this module is a
thin, deploy-friendly entrypoint.

Run locally::

    pip install -r requirements.txt
    python server.py            # serves MCP over streamable HTTP at /mcp
"""

from __future__ import annotations

from wynxx_mcp.server import build_server

# Module-level app so ASGI servers / tooling can import `server:mcp` if desired.
mcp = build_server()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

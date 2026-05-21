"""Smoke-test MCP client for the Wynxx server.

Connects to a running Wynxx MCP server over streamable HTTP, lists the tools,
and calls a read-only and an advisory tool, printing the structured results.

Usage (with the server running in another terminal):

    python scripts/smoke_client.py
    python scripts/smoke_client.py http://localhost:8080/mcp
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://localhost:8080/mcp"


async def main(url: str) -> None:
    print(f"Connecting to {url}\n")
    async with (
        streamablehttp_client(url) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        print("Discovered tools:")
        for tool in tools.tools:
            ro = (tool.annotations and tool.annotations.readOnlyHint) or False
            print(f"  - {tool.name}  (read-only: {ro})")

        print("\nanalyze_repository(payments-service):")
        result = await session.call_tool(
            "analyze_repository",
            {"repository_path": "payments-service", "language": "java", "depth": "deep"},
        )
        print(json.dumps(result.structuredContent, indent=2)[:900], "...")

        print("\ngenerate_tests(payments-service, coverage_target=90):")
        result = await session.call_tool(
            "generate_tests",
            {"repository_path": "payments-service", "coverage_target": 90},
        )
        data = result.structuredContent
        print("  status:", data.get("status"))
        print("  generated_files:", [f["path"] for f in data.get("generated_files", [])])
        print("  warnings:", data.get("warnings"))
        print("  trace_id:", data.get("metadata", {}).get("trace_id"))

    print("\nOK - server reachable and tools callable.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))

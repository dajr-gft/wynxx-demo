"""Raw MCP-client probe of the Wynxx MCP server (no ADK, no model).

Connects over streamable HTTP exactly like ADK's McpToolset does under the hood,
lists the Wynxx tools, and calls one. Proves the Wynxx side of the integration.
"""

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8080/mcp"


async def main() -> None:
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print(f"Discovered {len(tools)} Wynxx tools:")
            for t in tools:
                ro = (t.annotations.readOnlyHint if t.annotations else None)
                print(f"  - {t.name:<28} readOnly={ro}")

            print("\nCalling analyze_repository(payments-service)...")
            result = await session.call_tool(
                "analyze_repository",
                {"repository_path": "payments-service", "language": "java"},
            )
            payload = result.structuredContent or {}
            # Trim to the interesting fields for a readable proof.
            keys = [k for k in ("repository_path", "language", "summary", "findings") if k in payload]
            print(json.dumps({k: payload[k] for k in keys}, indent=2)[:900])


if __name__ == "__main__":
    asyncio.run(main())
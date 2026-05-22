"""Real ADK <-> Wynxx integration against the NATIVE @wynxx/mcp server.

Unlike ``integration_real.py`` (which talks HTTP to the repo's reference MCP
server), this drives the **real product**: it launches ``npx @wynxx/mcp`` over
stdio through ADK's ``McpToolset`` and discovers/invokes the live Wynxx tools
against a real instance.

The ``@wynxx/mcp`` server authenticates via OAuth — a browser window opens on
first connect; complete the login when prompted. Tool discovery/invocation
needs no Gemini credentials (only a full LLM-driven agent run would).

Run (from integrations/adk-agent-workflow):
    .venv/Scripts/python.exe integration_real_native.py
Optionally override the instance with WYNXX_INSTANCE=<host> before the command.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys

from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StdioServerParameters,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

INSTANCE = os.environ.get("WYNXX_INSTANCE", "34.71.69.43.nip.io")
LANGUAGE = os.environ.get("WYNXX_LANGUAGE", "pt-BR")
AZURE_REGISTRY = (
    "https://pkgs.dev.azure.com/gft-assets/ai-impact-feed/"
    "_packaging/ai-impact-feed/npm/registry/"
)


def _npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx.cmd"


async def main() -> None:
    # The Azure-feed auth is taken from the user's global ~/.npmrc; we only need
    # to point the @wynxx scope at the private feed so npx can resolve it.
    env = dict(os.environ)
    env["npm_config_@wynxx:registry"] = AZURE_REGISTRY

    params = StdioConnectionParams(
        server_params=StdioServerParameters(
            command=_npx(),
            args=["-y", "@wynxx/mcp", "--instance", INSTANCE, "--language", LANGUAGE],
            env=env,
        ),
        timeout=600,
    )
    toolset = McpToolset(connection_params=params)

    print(f">> Launching native @wynxx/mcp against {INSTANCE} (lang={LANGUAGE})")
    print(">> A browser may open for OAuth login — complete it to continue.\n", flush=True)

    tools = await toolset.get_tools()
    print(f"Discovered {len(tools)} real Wynxx tools via ADK's McpToolset:\n")
    for t in tools:
        desc = (getattr(t, "description", "") or "").strip().splitlines()
        first = desc[0] if desc else ""
        print(f"  - {t.name:<32} {first[:70]}")

    # Prove a real round-trip (not just discovery) with safe, read-only tools.
    print("\n>> Invoking read-only tools through the ADK MCP session...")
    session = await toolset._mcp_session_manager.create_session()
    for name in ("authenticate", "list_llms"):
        try:
            res = await session.call_tool(name, {})
            if getattr(res, "structuredContent", None):
                text = str(res.structuredContent)
            elif getattr(res, "content", None):
                text = " ".join(getattr(c, "text", "") or "" for c in res.content)
            else:
                text = "(empty)"
            flag = "ERROR" if getattr(res, "isError", False) else "OK"
            print(f"  [{flag}] {name}: {text.strip()[:300]}")
        except Exception as exc:  # noqa: BLE001 - probe should report, not crash
            print(f"  [FAIL] {name}: {type(exc).__name__}: {exc}")

    await toolset.close()
    print("\nReal ADK <-> Wynxx (native @wynxx/mcp) wire is LIVE.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)

"""Run a REAL Wynxx job end-to-end through the native @wynxx/mcp over ADK.

authenticate -> select the Gemini LLM -> run the Code Documenter on an inline
Python snippet, and print the real generated documentation (or the real error).
No Gemini/Vertex credentials are needed on our side: Wynxx runs the model.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil

from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StdioServerParameters,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

INSTANCE = os.environ.get("WYNXX_INSTANCE", "34.71.69.43.nip.io")
AZURE = (
    "https://pkgs.dev.azure.com/gft-assets/ai-impact-feed/"
    "_packaging/ai-impact-feed/npm/registry/"
)

SAMPLE = '''def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number (0-indexed)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''


def _npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx.cmd"


def _text(res) -> str:
    if getattr(res, "structuredContent", None):
        return json.dumps(res.structuredContent, indent=2, ensure_ascii=False)
    if getattr(res, "content", None):
        return " ".join(getattr(c, "text", "") or "" for c in res.content)
    return "(empty)"


async def main() -> None:
    env = dict(os.environ)
    env["npm_config_@wynxx:registry"] = AZURE
    params = StdioConnectionParams(
        server_params=StdioServerParameters(
            command=_npx(),
            args=["-y", "@wynxx/mcp", "--instance", INSTANCE, "--language", "pt-BR"],
            env=env,
        ),
        timeout=900,
    )
    toolset = McpToolset(connection_params=params)
    session = await toolset._mcp_session_manager.create_session()

    print(">> authenticate:", _text(await session.call_tool("authenticate", {}))[:60], "...")
    print(">> set_llm:", _text(await session.call_tool("set_llm", {"llmNameOrId": "Gemini"}))[:160])

    print("\n>> run_documenter on fibonacci.py (real Wynxx Code Documenter job)...\n")
    res = await session.call_tool(
        "run_documenter",
        {
            "sourceCodeLanguage": "Python",
            "fileName": "fibonacci.py",
            "fileContent": SAMPLE,
            "promptId": "DocumentCode_V5",
            "audience": "Software Engineer",
            "responseLanguage": "pt-BR",
        },
    )
    flag = "ERROR" if getattr(res, "isError", False) else "OK"
    print(f"[{flag}] run_documenter result:\n")
    print(_text(res)[:4000])

    await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())

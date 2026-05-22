"""Explore the real Wynxx instance through the native @wynxx/mcp over ADK stdio.

Read-only: authenticates, dumps the input schemas of the main job tools, and
lists the real configured catalogs (projects, jobs, prompts, audiences) so we
can drive a real end-to-end job next.
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

SCHEMA_TOOLS = {
    "set_llm", "set_repo", "set_pull_request", "set_doc_prompt", "set_audience",
    "set_test_prompt", "run_review", "start_review", "run_full_review",
    "run_documenter", "start_repo_documenter", "run_repo_documenter",
    "start_tester", "run_tester", "get_project", "get_backlog", "get_work_item",
}
LIST_TOOLS = (
    "list_projects", "list_jobs", "list_job_types", "list_doc_prompts",
    "list_audiences", "list_test_prompts", "list_sast_types",
)


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
        timeout=600,
    )
    toolset = McpToolset(connection_params=params)
    session = await toolset._mcp_session_manager.create_session()

    print("=== input schemas (job tools) ===")
    for t in (await session.list_tools()).tools:
        if t.name in SCHEMA_TOOLS:
            schema = t.inputSchema or {}
            props = schema.get("properties", {})
            req = schema.get("required", [])
            print(f"\n{t.name}  required={req}")
            for k, v in props.items():
                d = (v.get("description") or "").splitlines()
                print(f"   - {k}: {v.get('type', '?')}  {d[0][:70] if d else ''}")

    print("\n=== authenticate ===")
    print(_text(await session.call_tool("authenticate", {}))[:120])

    for name in LIST_TOOLS:
        print(f"\n=== {name} ===")
        try:
            print(_text(await session.call_tool(name, {}))[:1200])
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: {type(exc).__name__}: {exc}")

    await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())

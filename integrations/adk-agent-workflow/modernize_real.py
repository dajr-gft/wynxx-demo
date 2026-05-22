"""Test Gemini 3.1 Pro (preview) driving the agentic modernization target.

A single ADK LlmAgent on gemini-3.1-pro-preview (Vertex global endpoint) connects
to the repo's MCP server over HTTP and asks for a modernization assessment
targeting an agent-based architecture (target_platform=agent_engine). Prints the
Pro model's tool call and final synthesis.

Prereq: the repo MCP server running at SDLC_MCP_URL (default localhost:8080):
    ( cd ../cloud-run-mcp-server && WYNXX_MODE=stub python server.py )

Run (from integrations/adk-agent-workflow):
    .venv/Scripts/python.exe modernize_real.py
"""

from __future__ import annotations

import asyncio
import os
import warnings

warnings.filterwarnings("ignore")

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "wynxx-tests")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")  # Gemini 3 lives on global

from google.adk import Agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools.mcp_tool.mcp_session_manager import (  # noqa: E402
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset  # noqa: E402
from google.genai import types  # noqa: E402

MODEL = os.environ.get("SDLC_MODEL", "gemini-3.1-pro-preview")
MCP_URL = os.environ.get("SDLC_MCP_URL", "http://127.0.0.1:8080/mcp")
PROMPT = (
    "Run a modernization assessment for the repository 'payments-service' targeting "
    "an agent-based architecture (target_platform=agent_engine). Then summarize the "
    "target architecture, the migration phases and the key risks, in English."
)


async def main() -> None:
    tools = McpToolset(connection_params=StreamableHTTPConnectionParams(url=MCP_URL))
    agent = Agent(
        name="modernization_advisor",
        model=MODEL,
        instruction=(
            "You are a senior Google Cloud modernization architect. Use the Wynxx "
            "modernization_assessment tool with the requested target_platform, then "
            "summarize faithfully from the tool result — do not invent details. If the "
            "result includes a `diagram` field, reproduce it VERBATIM inside a ```mermaid "
            "fenced code block so it renders as a diagram."
        ),
        tools=[tools],
    )
    runner = InMemoryRunner(agent=agent, app_name="modernize")
    session = await runner.session_service.create_session(app_name="modernize", user_id="djalma")

    print(f">> model={MODEL}  (Vertex global)  mcp={MCP_URL}")
    print(f">> prompt: {PROMPT}\n")

    content = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    async for event in runner.run_async(
        user_id="djalma", session_id=session.id, new_message=content
    ):
        for part in (event.content.parts if event.content else []):
            if getattr(part, "function_call", None):
                args = dict(part.function_call.args or {})
                print(f"  [tool call]   {part.function_call.name}({args})")
            elif getattr(part, "function_response", None):
                resp = str(part.function_response.response)[:150]
                print(f"  [tool result] {part.function_response.name}: {resp}")
            elif getattr(part, "text", None) and event.is_final_response():
                print(f"\n=== {MODEL} synthesis ===\n{part.text}")

    await tools.close()


if __name__ == "__main__":
    asyncio.run(main())

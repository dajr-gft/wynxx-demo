"""Run the full SDLC orchestration (root_agent) via an ADK Runner.

Drives the real ``SequentialAgent`` + ``ParallelAgent`` graph against the Wynxx
MCP server at ``SDLC_MCP_URL`` (HTTP), with the human-in-the-loop gate
pre-approved (session state ``approved=True``) for an unattended end-to-end run.
Models default to Gemini 3 on the Vertex global endpoint.

Prereqs: ADC (Vertex) and an MCP server at ``SDLC_MCP_URL`` — e.g. run the repo's
cloud-run-mcp-server locally:  ``WYNXX_MODE=stub python server.py``.

Run (from integrations/adk-agent-workflow):
  .venv/Scripts/python.exe run_workflow_real.py
"""

from __future__ import annotations

import asyncio
import os
import warnings

warnings.filterwarnings("ignore")

os.environ.setdefault("SDLC_MODE", "real")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "wynxx-tests")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("SDLC_MCP_URL", "http://127.0.0.1:8080/mcp")

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from sdlc_workflow.agent import root_agent  # noqa: E402

PROMPT = os.environ.get(
    "SDLC_PROMPT", "Run the SDLC workflow for the repository 'payments-service'."
)


async def main() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="sdlc")
    session = await runner.session_service.create_session(
        app_name="sdlc", user_id="djalma", state={"approved": True}
    )
    print(f">> root_agent={root_agent.name}  model_pro/flash via Vertex global\n")

    content = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    async for event in runner.run_async(
        user_id="djalma", session_id=session.id, new_message=content
    ):
        who = event.author or "?"
        for part in (event.content.parts if event.content else []):
            if getattr(part, "function_call", None):
                print(f"  [{who} -> tool] {part.function_call.name}")
            elif getattr(part, "text", None) and part.text.strip():
                print(f"  [{who}] {part.text.strip()[:200]}")

    final = await runner.session_service.get_session(
        app_name="sdlc", user_id="djalma", session_id=session.id
    )
    print("\nfinal state keys:", sorted(final.state.keys()))

    # Memory (official agentic component): persist this run so a future session can
    # recall it via the analyst's preload_memory tool. InMemoryRunner uses an
    # in-memory store; on Vertex AI Agent Engine this is the managed Memory Bank.
    await runner.memory_service.add_session_to_memory(final)
    print("session persisted to memory (recall via preload_memory)")


if __name__ == "__main__":
    asyncio.run(main())

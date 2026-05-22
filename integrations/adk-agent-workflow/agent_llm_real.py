"""LLM-driven ADK agent over the REAL Wynxx MCP (native @wynxx/mcp).

A single Gemini-powered ADK agent equipped with the native Wynxx McpToolset
(stdio). The LLM decides which real Wynxx tools to call to satisfy a
natural-language request. The model reasoning runs on Vertex AI; the tool calls
hit the live Wynxx instance.

Prereqs (see SETUP_REAL.md):
  - gcloud auth application-default login   (ADC)
  - Vertex AI enabled on the project        (GOOGLE_CLOUD_PROJECT)

Run (from integrations/adk-agent-workflow):
  .venv/Scripts/python.exe agent_llm_real.py
"""

from __future__ import annotations

import asyncio
import os
import shutil
import warnings

warnings.filterwarnings("ignore")

# --- Vertex AI: where the agent's Gemini reasoning runs ---------------------
# Gemini 3 models are served on the global endpoint.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "wynxx-tests")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from google.adk import Agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools.mcp_tool.mcp_session_manager import (  # noqa: E402
    StdioConnectionParams,
    StdioServerParameters,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset  # noqa: E402
from google.genai import types  # noqa: E402

INSTANCE = os.environ.get("WYNXX_INSTANCE", "34.71.69.43.nip.io")
MODEL = os.environ.get("SDLC_MODEL", "gemini-3.5-flash")
AZURE = (
    "https://pkgs.dev.azure.com/gft-assets/ai-impact-feed/"
    "_packaging/ai-impact-feed/npm/registry/"
)
PROMPT = (
    "Usando as ferramentas do Wynxx: liste os projetos disponíveis e os LLMs "
    "disponíveis, e então me dê um resumo em português do que você encontrou."
)


def _npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx.cmd"


async def main() -> None:
    env = dict(os.environ)
    env["npm_config_@wynxx:registry"] = AZURE

    wynxx_tools = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_npx(),
                args=["-y", "@wynxx/mcp", "--instance", INSTANCE, "--language", "pt-BR"],
                env=env,
            ),
            timeout=600,
        )
    )

    agent = Agent(
        name="wynxx_pilot",
        model=MODEL,
        instruction=(
            "Você orquestra a plataforma Wynxx via MCP. Use as ferramentas "
            "disponíveis para responder ao pedido do usuário. Prefira ferramentas "
            "read-only (list_*, get_*). Responda em português."
        ),
        tools=[wynxx_tools],
    )

    runner = InMemoryRunner(agent=agent, app_name="wynxx_pilot")
    session = await runner.session_service.create_session(
        app_name="wynxx_pilot", user_id="djalma"
    )

    print(f">> model={MODEL}  (Vertex project={os.environ['GOOGLE_CLOUD_PROJECT']})")
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
                txt = str(part.function_response.response)
                print(f"  [tool result] {part.function_response.name}: {txt[:140]}")
            elif getattr(part, "text", None) and event.is_final_response():
                print(f"\n=== Resposta final do agente (LLM) ===\n{part.text}")

    await wynxx_tools.close()


if __name__ == "__main__":
    asyncio.run(main())

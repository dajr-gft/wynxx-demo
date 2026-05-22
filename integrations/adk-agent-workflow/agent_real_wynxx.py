"""A REAL ADK agent over the native @wynxx/mcp (the live Wynxx product).

Unlike the stub-backed ``sdlc_workflow``, every tool call here hits the live Wynxx
instance. A single Gemini ``LlmAgent`` reasons and drives the real Code Documenter
end to end: ``authenticate`` -> ``set_llm("Gemini")`` -> ``run_documenter`` on a
real file, then returns the real generated documentation.

A single, sequential agent (no ParallelAgent) is used on purpose: the @wynxx/mcp
stdio session does not tolerate concurrent calls, and a scoped tool surface keeps
Gemini's function-calling clean.

Run (from integrations/adk-agent-workflow):
  .venv/Scripts/python.exe agent_real_wynxx.py

Needs: ADC for the agent's own Gemini (Vertex, global endpoint) and a one-time
browser OAuth for Wynxx (a tab opens on first connect — sign in).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import warnings

warnings.filterwarnings("ignore")

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "wynxx-tests")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools.mcp_tool.mcp_session_manager import (  # noqa: E402
    StdioConnectionParams,
    StdioServerParameters,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset  # noqa: E402
from google.genai import types  # noqa: E402

INSTANCE = os.environ.get("WYNXX_INSTANCE", "34.71.69.43.nip.io")
AZURE = (
    "https://pkgs.dev.azure.com/gft-assets/ai-impact-feed/"
    "_packaging/ai-impact-feed/npm/registry/"
)
# The agent's OWN reasoning model (Vertex). Wynxx runs its own model server-side.
MODEL = os.environ.get("WYNXX_AGENT_MODEL", "gemini-3.5-flash")

SAMPLE = '''def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number (0-indexed)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''

INSTRUCTION = """
You document source code using the live Wynxx platform tools. Perform EXACTLY these
steps, one tool call at a time, in order:
1. Call `authenticate` with no arguments to sign in to Wynxx.
2. Call `set_llm` with llmNameOrId="Gemini".
3. Call `run_documenter` with sourceCodeLanguage="Python", the fileName and
   fileContent provided by the user, promptId="DocumentCode_V5",
   audience="Software Engineer", responseLanguage="pt-BR".
Then output the generated documentation from the run_documenter result, verbatim.
If a tool returns an error, report that error and stop — do not invent content.
""".strip()


def _npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx.cmd"


async def main() -> None:
    env = dict(os.environ)
    env["npm_config_@wynxx:registry"] = AZURE
    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_npx(),
                args=["-y", "@wynxx/mcp", "--instance", INSTANCE, "--language", "pt-BR"],
                env=env,
            ),
            timeout=900,
        ),
        tool_filter=["authenticate", "set_llm", "run_documenter"],
    )

    agent = LlmAgent(
        name="wynxx_documenter",
        model=MODEL,
        instruction=INSTRUCTION,
        tools=[toolset],
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )

    runner = InMemoryRunner(agent=agent, app_name="wynxx-real")
    session = await runner.session_service.create_session(
        app_name="wynxx-real", user_id="djalma"
    )
    prompt = f"Document this code. fileName=fibonacci.py\n\n{SAMPLE}"
    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    print(f">> agent={agent.name}  model={MODEL}  Wynxx instance={INSTANCE}")
    print(">> a browser tab may open for Wynxx OAuth on first connect — sign in.\n")
    async for event in runner.run_async(
        user_id="djalma", session_id=session.id, new_message=content
    ):
        who = event.author or "?"
        for part in event.content.parts if event.content else []:
            if getattr(part, "function_call", None):
                print(f"  [{who} -> tool] {part.function_call.name}")
            elif getattr(part, "text", None) and part.text.strip():
                print(f"  [{who}] {part.text.strip()[:1800]}")

    await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())

"""A REAL multi-tool ADK agent over the native @wynxx/mcp (live Wynxx product).

A single Gemini ``LlmAgent`` that drives TWO real Wynxx generation tools on the
same source file, end to end:
  authenticate -> set_llm("Gemini") -> run_documenter -> run_tester
returning the real generated documentation AND the real generated unit tests.

Notes on the real product (discovered from the live tool schemas):
  * documenter and tester operate on code directly (filePath / fileContent).
  * the reviewer (run_review / start_review) and the code fixer are VCS-based
    (they need a real Pull Request / repo configured in Wynxx), so a closed
    review->fix loop requires VCS integration and is intentionally out of scope
    for this inline demo.

A single, sequential agent with a scoped tool surface avoids the @wynxx/mcp stdio
concurrency limits and keeps Gemini's function-calling clean.

Run (from integrations/adk-agent-workflow):
  .venv/Scripts/python.exe agent_real_pipeline.py
Needs ADC for the agent's own Gemini (Vertex, global) + a browser OAuth for Wynxx.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
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


def _npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx.cmd"


async def main() -> None:
    # Write the sample to a real local file so the Wynxx tools can read it by path.
    tmp = tempfile.mkdtemp(prefix="wynxx_pipeline_")
    fpath = os.path.join(tmp, "fibonacci.py")
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE)

    instruction = f"""
You are an SDLC agent that uses the LIVE Wynxx platform tools. Perform EXACTLY these
steps, one tool call at a time, in order:
1. Call `authenticate` with no arguments.
2. Call `set_llm` with llmNameOrId="Gemini".
3. Call `run_documenter` with sourceCodeLanguage="Python", filePath="{fpath}",
   promptId="DocumentCode_V5", audience="Software Engineer", responseLanguage="pt-BR".
4. Call `run_tester` to generate unit tests for that same file: pass the file via its
   filePath ("{fpath}") in the `files` array, testType="unit",
   sourceCodeLanguage="Python", testingFrameworks="pytest".
Then report two sections: "## Documentation" (from run_documenter) and
"## Generated Tests" (from run_tester), verbatim from the tool results. If a tool
returns an error, report that error and continue to the next step.
""".strip()

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
        tool_filter=["authenticate", "set_llm", "run_documenter", "run_tester"],
    )

    agent = LlmAgent(
        name="wynxx_pipeline",
        model=MODEL,
        instruction=instruction,
        tools=[toolset],
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )

    runner = InMemoryRunner(agent=agent, app_name="wynxx-real")
    session = await runner.session_service.create_session(
        app_name="wynxx-real", user_id="djalma"
    )
    content = types.Content(
        role="user",
        parts=[types.Part(text=f"Document and generate unit tests for {fpath}")],
    )

    print(f">> agent={agent.name}  model={MODEL}  Wynxx={INSTANCE}")
    print(f">> file: {fpath}")
    print(">> a browser tab may open for Wynxx OAuth — sign in.\n")
    async for event in runner.run_async(
        user_id="djalma", session_id=session.id, new_message=content
    ):
        who = event.author or "?"
        for part in event.content.parts if event.content else []:
            if getattr(part, "function_call", None):
                print(f"  [{who} -> tool] {part.function_call.name}")
            elif getattr(part, "text", None) and part.text.strip():
                print(f"  [{who}] {part.text.strip()[:2500]}")

    await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())

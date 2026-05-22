"""Real ADK <-> Wynxx integration check.

Imports sdlc_workflow.agent in SDLC_MODE=real so the module builds the actual
ADK agents (each scoped to its single Wynxx tool, per Google Cloud's "progressive
disclosure" guidance), verifies that scoping, then discovers the full contract and
invokes one tool through a standalone probe McpToolset against a running Wynxx MCP
server. Tool discovery/invocation needs no Gemini credentials; only a full
LLM-driven agent run would.
"""

import asyncio
import os

os.environ.setdefault("SDLC_MODE", "real")
os.environ.setdefault("SDLC_MCP_URL", "http://127.0.0.1:8080/mcp")

EXPECTED = {
    "analyze_repository",
    "explain_code",
    "generate_documentation_draft",
    "modernization_assessment",
    "generate_tests",
    "review_code",
}


async def main() -> None:
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

    from sdlc_workflow import agent
    from sdlc_workflow.config import get_config

    cfg = get_config()
    print(f"config: mode={cfg.mode}  mcp_url={cfg.mcp_url}")
    print(f"models: pro={cfg.model_pro}  flash={cfg.model_flash}")

    # Each agent is scoped to exactly the one Wynxx tool it should call — this
    # minimal function-calling surface reduces Gemini MALFORMED_FUNCTION_CALL.
    scoped = [
        (agent.repo_analyst, "analyze_repository"),
        (agent.doc_writer, "generate_documentation_draft"),
        (agent.test_strategist, "generate_tests"),
        (agent.modernization_advisor, "modernization_assessment"),
    ]
    print("\nADK Agents built (real mode), tool scoping:")
    for a, expected in scoped:
        names = {t.name for t in await a.tools[0].get_tools()}
        print(f"  - {a.name:<22} model={a.model}  tools={sorted(names)}")
        assert names == {expected}, f"{a.name} should expose only {expected}, got {names}"
    print("Each agent is scoped to its single Wynxx tool: OK")

    # Discover the full 6-tool contract + invoke one tool via a standalone probe.
    probe = McpToolset(connection_params=StreamableHTTPConnectionParams(url=cfg.mcp_url))
    tools = await probe.get_tools()
    names = {t.name for t in tools}
    print(f"\nFull contract via a probe McpToolset: {len(tools)} tools")
    missing = EXPECTED - names
    assert not missing, f"missing expected Wynxx tools: {missing}"
    print("All 6 expected Wynxx tools discovered: OK")

    session = await probe._mcp_session_manager.create_session()
    res = await session.call_tool(
        "review_code",
        {"repository_path": "payments-service", "ruleset": "security"},
    )
    sc = res.structuredContent or {}
    print("\nADK-side call review_code(payments-service, ruleset=security):")
    print(f"  repository_path={sc.get('repository_path')}  ruleset={sc.get('ruleset')}")
    findings = sc.get("findings") or sc.get("issues") or []
    print(f"  findings returned: {len(findings)}")

    await probe.close()
    print("\nIntegration check complete: ADK <-> Wynxx MCP wire is live.")


if __name__ == "__main__":
    asyncio.run(main())
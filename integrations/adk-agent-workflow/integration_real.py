"""Real ADK <-> Wynxx integration check.

Imports sdlc_workflow.agent in SDLC_MODE=real so the module builds the actual
ADK McpToolset + four google.adk.Agent singletons (the article's code path),
then drives the shared toolset against a running Wynxx MCP server to discover and
invoke its tools. Tool discovery/invocation needs no Gemini credentials; only a
full LLM-driven agent run would.
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
    from sdlc_workflow import agent
    from sdlc_workflow.config import get_config

    cfg = get_config()
    print(f"config: mode={cfg.mode}  mcp_url={cfg.mcp_url}")
    print(f"models: pro={cfg.model_pro}  flash={cfg.model_flash}")

    agents = [
        agent.repo_analyst,
        agent.doc_writer,
        agent.test_strategist,
        agent.modernization_advisor,
    ]
    print("\nADK Agents built (real mode):")
    for a in agents:
        print(f"  - {a.name:<22} model={a.model}")

    # All four agents must share the one Wynxx McpToolset (per agent.py).
    shared = agent.wynxx_tools
    assert all(a.tools[0] is shared for a in agents), "agents must share one toolset"
    print("\nAll four agents share a single Wynxx McpToolset: OK")

    # The toolset connects to the Wynxx MCP server and discovers its tools.
    tools = await shared.get_tools()
    names = {t.name for t in tools}
    print(f"\nMcpToolset.get_tools() returned {len(tools)} tools via ADK:")
    for t in tools:
        print(f"  - {t.name}")

    missing = EXPECTED - names
    assert not missing, f"missing expected Wynxx tools: {missing}"
    print("\nAll 6 expected Wynxx tools discovered through ADK's McpToolset: OK")

    # Invoke one tool through the ADK toolset's MCP session manager (no model).
    session = await shared._mcp_session_manager.create_session()
    res = await session.call_tool(
        "review_code",
        {"repository_path": "payments-service", "ruleset": "security"},
    )
    sc = res.structuredContent or {}
    print("\nADK-side call review_code(payments-service, ruleset=security):")
    print(f"  repository_path={sc.get('repository_path')}  ruleset={sc.get('ruleset')}")
    findings = sc.get("findings") or sc.get("issues") or []
    print(f"  findings returned: {len(findings)}")

    await shared.close()
    print("\nIntegration check complete: ADK <-> Wynxx MCP wire is live.")


if __name__ == "__main__":
    asyncio.run(main())
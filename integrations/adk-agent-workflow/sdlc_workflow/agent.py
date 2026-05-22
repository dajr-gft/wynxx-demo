# Copyright 2026 GFT Technologies SE.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SDLC orchestration agent — an ADK 2.0 workflow over the Wynxx MCP server.

Most enterprise SDLC flows are deterministic graphs, not free-form agent loops.
This agent analyzes a repository once, fans the findings out to three parallel
agents — documentation, tests, and modernization — and fans them back in at a
human-in-the-loop approval gate before any artifact is published.

* ``SDLC_MODE=real`` builds the genuine ADK 2.0 orchestration with
  ``SequentialAgent`` + ``ParallelAgent`` (``google.adk.agents``) and a
  human-in-the-loop gate implemented as a ``before_agent_callback``. ``root_agent``
  is a real ADK agent, deployable to Vertex AI Agent Engine (``deployment/deploy.py``)
  and runnable through an ADK ``Runner`` (see ``agent_llm_real.py``).
* ``SDLC_MODE=stub`` (default) runs the same topology on a self-contained runtime
  (``graph.py``) with deterministic stub agents, so the example runs in CI and
  offline with no models or MCP server.

Following the adk-samples convention, agents are module-level singletons and
prompts live in ``prompt.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .config import RunMode, get_config
from .prompt import (
    DOC_WRITER_INSTRUCTION,
    MODERNIZATION_ADVISOR_INSTRUCTION,
    REPO_ANALYST_INSTRUCTION,
    REVIEW_PUBLISH_INSTRUCTION,
    TEST_STRATEGIST_INSTRUCTION,
    WORKFLOW_DESCRIPTION,
)

_config = get_config()


if _config.mode is RunMode.REAL:
    # -----------------------------------------------------------------------
    # Real ADK 2.0 orchestration — SequentialAgent + ParallelAgent + HITL gate.
    # `root_agent` is a genuine ADK agent: deploy it to Agent Engine or drive it
    # with an ADK Runner. Models default to Gemini 3 on the Vertex global endpoint.
    # -----------------------------------------------------------------------
    from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.google_llm import Gemini
    from google.adk.tools import preload_memory
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    from google.genai import types

    # Steady function-calling: temperature 0 reduces Gemini MALFORMED_FUNCTION_CALL.
    _STEADY = types.GenerateContentConfig(temperature=0.0)

    _MAX_MALFORMED_RETRIES = 2

    class _RetryingGemini(Gemini):
        """Gemini that retries a turn returning MALFORMED_FUNCTION_CALL.

        Preview models intermittently emit a malformed function call on large
        tool turns; the failure is transient, so re-running the same turn almost
        always succeeds. Responses are buffered per turn, so a malformed turn is
        discarded and retried before anything reaches the runner.
        """

        async def generate_content_async(self, llm_request, stream=False):
            for attempt in range(_MAX_MALFORMED_RETRIES + 1):
                buffered, malformed = [], False
                async for resp in super().generate_content_async(
                    llm_request, stream=stream
                ):
                    buffered.append(resp)
                    if resp.finish_reason == types.FinishReason.MALFORMED_FUNCTION_CALL:
                        malformed = True
                if not malformed or attempt == _MAX_MALFORMED_RETRIES:
                    for resp in buffered:
                        yield resp
                    return

    # Pro for reasoning, Flash for volume — both with automatic MALFORMED retry.
    _pro_model = _RetryingGemini(model=_config.model_pro)
    _flash_model = _RetryingGemini(model=_config.model_flash)

    def _toolset(*tool_names: str) -> McpToolset:
        """A Wynxx MCP toolset scoped to only the given tools (same MCP server).

        Each agent sees only the one tool it needs — "avoid tool bloat / use
        progressive disclosure" per Google Cloud's agentic-architecture guidance.
        The minimal function-calling surface also reduces Gemini's
        MALFORMED_FUNCTION_CALL versus exposing all tools to every agent.
        """
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=_config.mcp_url),
            tool_filter=list(tool_names),
        )

    # Different models for different roles: Pro for reasoning, Flash for volume.
    # Each agent is scoped to exactly the one Wynxx tool it should call.
    # `preload_memory` gives the analyst short/long-term Memory (official agentic
    # component): Vertex AI Agent Engine Sessions + Memory Bank in production.
    repo_analyst = LlmAgent(
        name="repo_analyst",
        model=_pro_model,
        instruction=REPO_ANALYST_INSTRUCTION,
        tools=[_toolset("analyze_repository"), preload_memory],
        output_key="findings",
        generate_content_config=_STEADY,
    )
    doc_writer = LlmAgent(
        name="doc_writer",
        model=_flash_model,
        instruction=DOC_WRITER_INSTRUCTION,
        tools=[_toolset("generate_documentation_draft")],
        output_key="docs",
        generate_content_config=_STEADY,
    )
    test_strategist = LlmAgent(
        name="test_strategist",
        model=_flash_model,
        instruction=TEST_STRATEGIST_INSTRUCTION,
        tools=[_toolset("generate_tests")],
        output_key="tests",
        generate_content_config=_STEADY,
    )
    modernization_advisor = LlmAgent(
        name="modernization_advisor",
        model=_pro_model,
        instruction=MODERNIZATION_ADVISOR_INSTRUCTION,
        tools=[_toolset("modernization_assessment")],
        output_key="modernization",
        generate_content_config=_STEADY,
    )

    # Fan-out: the three artifact agents run concurrently over the shared findings.
    fan_out = ParallelAgent(
        name="fan_out",
        description="Draft documentation, tests, and a modernization assessment in parallel.",
        sub_agents=[doc_writer, test_strategist, modernization_advisor],
    )

    def require_human_approval(callback_context: CallbackContext) -> types.Content | None:
        """Human-in-the-loop gate: block publishing until a human approves.

        ADK invokes ``before_agent_callback`` before the agent body. Returning a
        ``Content`` short-circuits the agent, so nothing is published until
        ``approved`` is set in session state (by an operator, a Gemini Enterprise
        action, or an upstream approval system). The gate is closed by default.
        """
        if not callback_context.state.get("approved", False):
            return types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="Human approval required before publishing SDLC artifacts. "
                        "Set state['approved']=True to proceed."
                    )
                ],
            )
        return None

    review_and_publish = LlmAgent(
        name="review_and_publish",
        model=_flash_model,
        instruction=REVIEW_PUBLISH_INSTRUCTION,
        before_agent_callback=require_human_approval,
        output_key="published_summary",
        generate_content_config=_STEADY,
    )

    # Fan-in: analyze -> parallel drafts -> human-gated publish.
    sdlc_workflow = SequentialAgent(
        name="sdlc_orchestration",
        description=WORKFLOW_DESCRIPTION,
        sub_agents=[repo_analyst, fan_out, review_and_publish],
    )
    root_agent = sdlc_workflow

    def run_workflow(
        repository_path: str,
        approver: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Not used in real mode — the ADK Runner / Agent Engine drives root_agent.

        Run the real agents with an ADK ``Runner`` (see ``agent_llm_real.py``) or
        deploy with ``deployment/deploy.py``.
        """
        raise NotImplementedError(
            "Real mode is driven by the ADK Runner / Agent Engine, not run_workflow(). "
            "Use a Runner over root_agent (see agent_llm_real.py) or deploy it."
        )

else:
    # -----------------------------------------------------------------------
    # Offline stub runtime — deterministic agents on the self-contained graph
    # (graph.py). Same topology, no models or MCP server required.
    # -----------------------------------------------------------------------
    from .graph import Workflow, node

    class _StubAgent:
        """Offline agent whose ``run`` returns deterministic structured output."""

        def __init__(self, name: str, producer: Callable[[Any], dict[str, Any]]) -> None:
            self.name = name
            self._producer = producer

        def run(self, payload: Any) -> dict[str, Any]:
            return self._producer(payload)

    repo_analyst = _StubAgent(
        "repo_analyst",
        lambda repository_path: {
            "repository_path": repository_path,
            "summary": "Spring Boot service; test and documentation gaps; "
            "containerization candidate.",
            "findings": [
                "Incomplete unit test coverage",
                "No architecture documentation",
                "Hard-coded datasource credentials (high risk)",
            ],
            "recommended_actions": ["generate_tests", "generate_documentation", "modernize"],
        },
    )
    doc_writer = _StubAgent(
        "doc_writer",
        lambda findings: {
            "artifacts": ["architecture-summary.md", "api-overview.md"],
            "summary": "Drafted an architecture summary and an API overview.",
        },
    )
    test_strategist = _StubAgent(
        "test_strategist",
        lambda findings: {
            "artifacts": ["test-recommendations.md"],
            "files": ["OrderServiceTest.java", "OrderControllerTest.java"],
            "coverage_target": 80,
        },
    )
    modernization_advisor = _StubAgent(
        "modernization_advisor",
        lambda findings: {
            "artifacts": ["modernization-assessment.md", "migration-plan-gcp.md"],
            "target_platform": "cloud_run",
            "effort_estimate": "4–6 person-weeks",
        },
    )

    @node(start=True)
    def analyze(state):
        findings = repo_analyst.run(state["repository_path"])
        return {"findings": findings}

    @node(after=analyze, fan_out=["document", "test", "modernize"])
    def fan_out(state):
        return state

    @node()
    def document(state):
        state["docs"] = doc_writer.run(state["findings"])
        return state

    @node()
    def test(state):
        state["tests"] = test_strategist.run(state["findings"])
        return state

    @node()
    def modernize(state):
        state["modernization"] = modernization_advisor.run(state["findings"])
        return state

    @node(after=["document", "test", "modernize"], human_in_the_loop=True)
    def review_and_publish(state):
        # Human approval gate before any artifact is written. The runtime only
        # runs this body once the gate is approved.
        artifacts: set[str] = set()
        for key in ("docs", "tests", "modernization"):
            artifacts.update(state.get(key, {}).get("artifacts", []))
        state["published"] = True
        state["artifacts"] = sorted(artifacts)
        return state

    # The deployable graph workflow. `root_agent` is the name ADK / deploy expects.
    sdlc_workflow = Workflow(
        name="sdlc_orchestration",
        nodes=[analyze, fan_out, document, test, modernize, review_and_publish],
    )
    root_agent = sdlc_workflow

    def run_workflow(
        repository_path: str,
        approver: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Run the workflow locally for one repository (stub / fallback runtime).

        ``approver(node_name, state) -> bool`` implements the human-in-the-loop gate.
        """
        return sdlc_workflow.run({"repository_path": repository_path}, approver=approver)

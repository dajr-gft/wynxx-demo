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

"""SDLC orchestration agent — an ADK 2.0 graph over the Wynxx MCP server.

Most enterprise SDLC flows are deterministic graphs, not free-form agent loops.
This agent analyzes a repository once, fans the findings out to three parallel
agents — documentation, tests, and modernization — and fans them back in at a
human-in-the-loop approval gate before any artifact is published.

Following the adk-samples convention, the agents are module-level singletons and
prompts live in ``prompt.py``. The graph runs on the real ADK 2.0 runtime when
``SDLC_MODE=real`` and on the local fallback runtime (``graph.py``) with
deterministic stub agents otherwise, so the example runs anywhere.

``root_agent`` is the deployable workflow (see ``deployment/deploy.py``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .config import RunMode, get_config
from .graph import Workflow, node
from .prompt import (
    DOC_WRITER_INSTRUCTION,
    MODERNIZATION_ADVISOR_INSTRUCTION,
    REPO_ANALYST_INSTRUCTION,
    TEST_STRATEGIST_INSTRUCTION,
)

_config = get_config()


# ---------------------------------------------------------------------------
# Agents — module-level singletons (real ADK, or offline stubs).
# ---------------------------------------------------------------------------


class _StubAgent:
    """Offline agent whose ``run`` returns deterministic structured output.

    Used when ``SDLC_MODE=stub`` (the default) so the graph runs without models
    or a live MCP server. In real mode these are ADK agents calling the Wynxx
    MCP tools; the structured shape is intentionally similar.
    """

    def __init__(self, name: str, producer: Callable[[Any], dict[str, Any]]) -> None:
        self.name = name
        self._producer = producer

    def run(self, payload: Any) -> dict[str, Any]:
        return self._producer(payload)


if _config.mode is RunMode.REAL:
    from google.adk import Agent
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

    # Every agent shares one toolset — the same Wynxx MCP server (Path A / B).
    wynxx_tools = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=_config.mcp_url),
    )

    # Different models for different roles: Pro for reasoning, Flash for volume.
    repo_analyst = Agent(
        name="repo_analyst",
        model=_config.model_pro,
        instruction=REPO_ANALYST_INSTRUCTION,
        tools=[wynxx_tools],
    )
    doc_writer = Agent(
        name="doc_writer",
        model=_config.model_flash,
        instruction=DOC_WRITER_INSTRUCTION,
        tools=[wynxx_tools],
    )
    test_strategist = Agent(
        name="test_strategist",
        model=_config.model_flash,
        instruction=TEST_STRATEGIST_INSTRUCTION,
        tools=[wynxx_tools],
    )
    modernization_advisor = Agent(
        name="modernization_advisor",
        model=_config.model_pro,
        instruction=MODERNIZATION_ADVISOR_INSTRUCTION,
        tools=[wynxx_tools],
    )
else:
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


# ---------------------------------------------------------------------------
# Graph — nodes and the workflow (the article's ADK 2.0 graph).
# ---------------------------------------------------------------------------


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
    # Human approval gate before any artifact is written. The runtime only runs
    # this body once the gate is approved.
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

    In a real Agent Runtime deployment the ADK runtime drives the graph; this
    helper is for local demos and tests. ``approver(node_name, state) -> bool``
    implements the human-in-the-loop gate.
    """
    return sdlc_workflow.run({"repository_path": repository_path}, approver=approver)

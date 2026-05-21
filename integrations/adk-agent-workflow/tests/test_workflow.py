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

"""Tests for the SDLC graph workflow (fallback runtime, stub agents)."""

from __future__ import annotations

import pytest

from sdlc_workflow.agent import run_workflow, sdlc_workflow
from sdlc_workflow.graph import USING_ADK


@pytest.mark.skipif(USING_ADK, reason="topology assertions target the local fallback runtime")
def test_graph_dependencies_model_fan_out_and_fan_in():
    deps = sdlc_workflow._deps
    # fan_out runs after analyze
    assert "analyze" in deps["fan_out"]
    # the three parallel nodes each depend on fan_out
    for parallel in ("document", "test", "modernize"):
        assert "fan_out" in deps[parallel]
    # the gate fans in from all three
    assert {"document", "test", "modernize"} <= deps["review_and_publish"]


def test_full_run_produces_all_artifacts_when_approved():
    state = run_workflow("payments-service", approver=lambda name, s: True)

    assert state["findings"]["repository_path"] == "payments-service"
    assert "docs" in state and "tests" in state and "modernization" in state
    assert state["approved"] is True
    assert state["published"] is True
    # Artifacts are the fan-in union of all three branches.
    assert "architecture-summary.md" in state["artifacts"]
    assert "test-recommendations.md" in state["artifacts"]
    assert "modernization-assessment.md" in state["artifacts"]


def test_rejected_gate_publishes_nothing():
    state = run_workflow("payments-service", approver=lambda name, s: False)

    assert state["approved"] is False
    assert state["status"] == "rejected"
    assert state["published"] is False
    # The publish body never ran, so no artifact list was produced.
    assert "artifacts" not in state


def test_default_approver_auto_approves_with_a_note():
    state = run_workflow("payments-service")

    assert state["approved"] is True
    assert state["published"] is True
    assert "auto-approved" in state["approval_note"]

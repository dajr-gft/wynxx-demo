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

"""Evaluation for the SDLC orchestration workflow.

Two layers, following the adk-samples eval convention:

* An offline *golden* check that runs the graph (stub mode) and compares the
  published artifact package to ``data/expected_artifacts.json``. Runs anywhere.
* An ADK ``AgentEvaluator`` run against ``data/sdlc_orchestration.evalset.json``,
  skipped automatically when the real ADK runtime / models are not available.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from sdlc_workflow.agent import run_workflow

DATA = pathlib.Path(__file__).parent / "data"


def test_published_artifacts_match_golden():
    expected = json.loads((DATA / "expected_artifacts.json").read_text(encoding="utf-8"))
    state = run_workflow(expected["repository_path"], approver=lambda name, s: True)
    assert state["artifacts"] == sorted(expected["artifacts"])


def test_adk_evalset_when_runtime_available():
    """Run the ADK evalset when google-adk + Vertex are configured; else skip."""
    evaluator = pytest.importorskip("google.adk.evaluation.agent_evaluator")
    import asyncio

    asyncio.run(
        evaluator.AgentEvaluator.evaluate(
            agent_module="sdlc_workflow",
            eval_dataset_file_path_or_dir=str(DATA / "sdlc_orchestration.evalset.json"),
        )
    )

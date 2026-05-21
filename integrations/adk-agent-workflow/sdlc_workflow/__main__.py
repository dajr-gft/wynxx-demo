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

"""Local demo entrypoint: ``python -m sdlc_workflow``.

Runs the graph end-to-end against the offline stub agents and prints the SDLC
artifact package, gated by a console human-in-the-loop approver.
"""

from __future__ import annotations

from typing import Any

from .agent import run_workflow


def _console_approver(node_name: str, state: dict[str, Any]) -> bool:
    print(f"[human-in-the-loop] '{node_name}' requests approval to publish:")
    for key in ("docs", "tests", "modernization"):
        for artifact in state.get(key, {}).get("artifacts", []):
            print(f"    - {artifact}")
    print("    -> auto-approving for this demo run")
    return True


def main() -> None:
    result = run_workflow("payments-service", approver=_console_approver)
    print("\nPublished SDLC package:")
    for artifact in result.get("artifacts", []):
        print(f"  {artifact}")


if __name__ == "__main__":
    main()

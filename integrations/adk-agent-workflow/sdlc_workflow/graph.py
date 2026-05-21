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

"""Graph workflow primitives — ADK 2.0 with a local fallback runtime.

ADK 2.0 introduces a graph-based workflow runtime (``node`` decorator,
``Workflow`` runner) with deterministic routing, fan-out/fan-in, retries, state
management, and human-in-the-loop nodes.

This module prefers the real ``google.adk.workflows`` primitives when they are
installed. When they aren't (for example in CI or a quick local demo), it falls
back to a compact, faithful implementation with the same semantics so the
example runs end-to-end today. The node/Workflow API is identical either way, so
the graph definition in ``agent.py`` does not change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

try:  # Prefer the real ADK 2.0 graph runtime when available.
    from google.adk.workflows import Workflow, node  # type: ignore

    USING_ADK = True
except ImportError:  # Local fallback — same surface, executes deterministically.
    USING_ADK = False

    State = dict[str, Any]
    NodeFn = Callable[[State], State | None]
    Approver = Callable[[str, State], bool]

    @dataclass
    class _Node:
        fn: NodeFn
        name: str
        start: bool = False
        after: list[str] = field(default_factory=list)
        fan_out: list[str] = field(default_factory=list)
        human_in_the_loop: bool = False

        def __call__(self, state: State) -> State | None:
            return self.fn(state)

    def _as_name_list(value: Any) -> list[str]:
        if value is None:
            return []
        items = value if isinstance(value, (list, tuple)) else [value]
        return [v.name if isinstance(v, _Node) else getattr(v, "__name__", str(v)) for v in items]

    def node(
        _fn: NodeFn | None = None,
        *,
        start: bool = False,
        after: Any = None,
        fan_out: list[str] | None = None,
        human_in_the_loop: bool = False,
    ):
        """Decorator that turns a function into a graph node."""

        def wrap(fn: NodeFn) -> _Node:
            return _Node(
                fn=fn,
                name=fn.__name__,
                start=start,
                after=_as_name_list(after),
                fan_out=list(fan_out or []),
                human_in_the_loop=human_in_the_loop,
            )

        return wrap(_fn) if _fn is not None else wrap

    class Workflow:  # noqa: D401 — mirrors the ADK 2.0 Workflow surface
        """Executes a graph of nodes with fan-out/fan-in and HITL gates."""

        def __init__(self, name: str, nodes: list[_Node]) -> None:
            self.name = name
            self.nodes: dict[str, _Node] = {n.name: n for n in nodes}
            self._deps = self._resolve_dependencies()

        def _resolve_dependencies(self) -> dict[str, set[str]]:
            deps: dict[str, set[str]] = {name: set(n.after) for name, n in self.nodes.items()}
            # A fan_out edge F -> [a, b, c] means a, b, c depend on F.
            for name, n in self.nodes.items():
                for target in n.fan_out:
                    deps.setdefault(target, set()).add(name)
            return deps

        def run(
            self,
            initial_state: State | None = None,
            approver: Approver | None = None,
        ) -> State:
            """Run the workflow to completion, returning the final state.

            ``approver`` is called for every human-in-the-loop node; returning
            ``False`` rejects the gate and the node body is skipped. When no
            approver is supplied, gates auto-approve (and say so in the state).
            """
            state: State = dict(initial_state or {})
            completed: set[str] = set()
            total = len(self.nodes)

            while len(completed) < total:
                ready = [
                    name
                    for name, n in self.nodes.items()
                    if name not in completed and self._deps.get(name, set()) <= completed
                ]
                if not ready:
                    raise RuntimeError(
                        f"Workflow '{self.name}' is stuck; check for a dependency cycle."
                    )
                # Deterministic order; in ADK runtime independent nodes run concurrently.
                for name in sorted(ready):
                    self._run_node(self.nodes[name], state, approver)
                    completed.add(name)
            return state

        @staticmethod
        def _run_node(n: _Node, state: State, approver: Approver | None) -> None:
            if n.human_in_the_loop:
                approved = approver(n.name, state) if approver else True
                state["approved"] = approved
                if approver is None:
                    state.setdefault("approval_note", "auto-approved (no approver supplied)")
                if not approved:
                    state["status"] = "rejected"
                    state["published"] = False
                    return
            result = n(state)
            if isinstance(result, dict):
                state.update(result)


__all__ = ["USING_ADK", "Workflow", "node"]

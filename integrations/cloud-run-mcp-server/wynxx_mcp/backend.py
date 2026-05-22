"""Backend abstraction — the single seam where real Wynxx integration plugs in.

The MCP toolsets never talk to a backend directly. They call
:meth:`WynxxBackend.invoke`, which is implemented twice:

* :class:`StubBackend` — deterministic, offline reference responses. This is
  what makes the example runnable with zero cloud dependencies.
* :class:`HttpBackend` — forwards the call to a live Wynxx REST backend (the
  ``real`` mode), enforcing a timeout and forwarding an optional auth token.

In a production deployment, ``HttpBackend`` is where you would also enforce
tenant-level authorization and translate the platform's native responses into
the tool payloads below.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from .config import BackendMode, Settings

# Tool name -> REST path on the live backend. Mirrors the Path B OpenAPI spec.
_ENDPOINTS: dict[str, str] = {
    "analyze_repository": "/analyze",
    "explain_code": "/explain",
    "generate_documentation_draft": "/generate-documentation",
    "modernization_assessment": "/modernization-assessment",
    "generate_tests": "/generate-tests",
    "review_code": "/review",
}


class BackendError(RuntimeError):
    """Raised when the live backend cannot fulfil a request."""


class WynxxBackend(Protocol):
    """Minimal contract every backend implementation must satisfy."""

    mode: str

    def invoke(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the domain payload for ``tool`` (without execution metadata)."""
        ...


class HttpBackend:
    """Calls a live Wynxx backend over HTTP (``WYNXX_MODE=real``)."""

    mode = BackendMode.REAL.value

    def __init__(self, settings: Settings) -> None:
        base_url = settings.require_real_backend()
        headers = {"Accept": "application/json"}
        # For a GCP service-to-service target (e.g. another Cloud Run service),
        # prefer a short-lived ID token minted for the target audience via
        # Application Default Credentials over a static token:
        #   from google.auth.transport.requests import Request
        #   from google.oauth2.id_token import fetch_id_token
        #   token = fetch_id_token(Request(), base_url)
        # A static token is supported here only to keep the example dependency-free.
        if settings.backend_token:
            headers["Authorization"] = f"Bearer {settings.backend_token}"
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=settings.backend_timeout_seconds,
        )

    def invoke(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = _ENDPOINTS.get(tool)
        if path is None:
            raise BackendError(f"Unknown tool: {tool}")
        try:
            response = self._client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:  # network/HTTP/decoding failures
            raise BackendError(f"Wynxx backend call '{tool}' failed: {exc}") from exc

    def close(self) -> None:
        self._client.close()


class StubBackend:
    """Deterministic, offline reference responses (``WYNXX_MODE=stub``).

    Responses are intentionally illustrative. They demonstrate the *shape* of a
    real SDLC assessment without requiring a backend, so the architecture stays
    the focus.
    """

    mode = BackendMode.STUB.value

    def invoke(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self, f"_{tool}", None)
        if handler is None:
            raise BackendError(f"Unknown tool: {tool}")
        return handler(payload)

    # -- read-only --------------------------------------------------------

    def _analyze_repository(self, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "Spring Boot service analyzed. Sound structure; test and "
            "documentation gaps; a clear candidate for containerization.",
            "findings": [
                {
                    "title": "Spring Boot application detected",
                    "detail": "Maven project targeting Java 17 with Spring Boot 3.x.",
                    "severity": "info",
                    "category": "architecture",
                },
                {
                    "title": "Incomplete unit test coverage",
                    "detail": "Service and controller layers have sparse tests.",
                    "severity": "medium",
                    "category": "testing",
                },
                {
                    "title": "Containerization candidate",
                    "detail": "Stateless HTTP service; no local disk dependencies.",
                    "severity": "low",
                    "category": "modernization",
                },
            ],
            "recommended_actions": [
                "Generate missing unit tests for the service layer",
                "Produce architecture and API documentation",
                "Run a modernization assessment targeting Cloud Run",
                "Define a deployment strategy for Google Cloud",
            ],
            "risks": [
                {
                    "title": "Hard-coded configuration",
                    "detail": "Datasource credentials read from application.properties.",
                    "severity": "high",
                    "category": "security",
                }
            ],
            "artifacts": [
                {"name": "analysis-report.json", "kind": "report", "uri": None},
            ],
        }

    def _explain_code(self, p: dict[str, Any]) -> dict[str, Any]:
        target = p.get("symbol") or p.get("file_path", "the selected code")
        return {
            "summary": f"{target} implements the order-processing entry point and "
            "delegates persistence to the repository layer.",
            "walkthrough": [
                "Validates the inbound request DTO.",
                "Maps the DTO to a domain entity.",
                "Persists via the repository and publishes a domain event.",
                "Returns a 201 response with the created resource location.",
            ],
            "key_components": ["OrderController", "OrderService", "OrderRepository"],
            "dependencies": ["spring-web", "spring-data-jpa", "jakarta.validation"],
            "complexity": "medium",
        }

    def _generate_documentation_draft(self, p: dict[str, Any]) -> dict[str, Any]:
        doc_type = p.get("doc_type", "architecture")
        return {
            "doc_type": doc_type,
            "title": f"{doc_type.title()} documentation (draft)",
            "format": "markdown",
            "sections": [
                {
                    "heading": "Overview",
                    "content": "Stateless REST service exposing order management APIs.",
                },
                {
                    "heading": "Components",
                    "content": "Controller, service, repository, and event publisher layers.",
                },
                {
                    "heading": "Runtime",
                    "content": "Packaged as a container; target runtime Cloud Run.",
                },
            ],
            "warnings": ["Draft generated from static analysis; review before publishing."],
        }

    # -- advisory ---------------------------------------------------------

    def _modernization_assessment(self, p: dict[str, Any]) -> dict[str, Any]:
        target = p.get("target_platform", "cloud_run")
        # An agent-based target re-architects the service into governed MCP tools
        # orchestrated by ADK agents on Agent Engine — not a container lift-and-shift.
        if target in ("agent_engine", "agentic", "agents"):
            return self._modernization_agentic()
        return {
            "current_state": "Monolithic Spring Boot service deployed on a VM with a "
            "co-located relational database.",
            "target_architecture": f"Containerized service on {target} with a managed "
            "Cloud SQL instance and Secret Manager for credentials.",
            "findings": [
                {
                    "title": "Stateless workload",
                    "detail": "No session affinity required; horizontally scalable.",
                    "severity": "info",
                    "category": "modernization",
                }
            ],
            "risks": [
                {
                    "title": "Embedded credentials",
                    "detail": "Move secrets to Secret Manager before migration.",
                    "severity": "high",
                    "category": "security",
                }
            ],
            "migration_phases": [
                {
                    "name": "Containerize",
                    "objective": "Produce a reproducible image.",
                    "effort": "S",
                },
                {
                    "name": "Externalize state",
                    "objective": "Migrate DB to Cloud SQL.",
                    "effort": "M",
                },
                {
                    "name": "Deploy",
                    "objective": "Ship to Cloud Run with CI/CD.",
                    "effort": "M",
                },
            ],
            "effort_estimate": "4–6 person-weeks",
            "recommendation": "Proceed with a phased migration to Cloud Run; address "
            "secret management first.",
        }

    def _modernization_agentic(self) -> dict[str, Any]:
        """Re-platform to an agentic architecture on the post-Next '26 GCP stack.

        Target: business capabilities exposed as governed MCP tools, orchestrated by
        ADK 2.0 agents (Gemini 3) on Vertex AI Agent Engine, governed end-to-end by
        Agent Gateway / Agent Identity / Agent Registry / Model Armor.
        """
        return {
            "current_state": "Monolithic Spring Boot service on a VM with a co-located "
            "database; capabilities are reachable only through a synchronous REST API, "
            "with no machine-discoverable tool contract for agents.",
            "target_architecture": (
                "Agentic re-platform on Google Cloud (post-Next '26). Expose the "
                "service's capabilities as Model Context Protocol (MCP) tools and "
                "orchestrate them with Agent Development Kit (ADK) 2.0 — Gemini 3.1 Pro "
                "(preview) for reasoning and Gemini 3.5 Flash for high-volume steps, on "
                "the Vertex AI global endpoint — running on Vertex AI Agent Engine. "
                "Publish the tools via a custom MCP server on Cloud Run or an Apigee MCP "
                "proxy over the existing REST API. Front every call with Agent Gateway "
                "(Agent Identity mTLS + DPoP, IAM Deny/IAP, Model Armor), discover them "
                "through Agent Registry, and emit Cloud Audit Logs + OpenTelemetry with "
                "BigQuery Agent Analytics for engineering intelligence. Vertex AI Model "
                "Garden keeps the design model-agnostic (Gemini 3, Claude, Llama, Gemma)."
            ),
            "findings": [
                {
                    "title": "Capabilities are not agent-consumable",
                    "detail": "A REST API exists, but there is no MCP tool contract, so "
                    "agents and Gemini surfaces (CLI, Code Assist, Gemini Enterprise) "
                    "cannot discover or call the service.",
                    "severity": "medium",
                    "category": "modernization",
                },
                {
                    "title": "Apigee MCP shortcut available",
                    "detail": "The existing REST API can be published as governed MCP "
                    "tools through an Apigee MCP proxy with no code change.",
                    "severity": "info",
                    "category": "modernization",
                },
                {
                    "title": "Deterministic workflow fit",
                    "detail": "The order flow is a deterministic graph — a fit for ADK "
                    "SequentialAgent/ParallelAgent with human-in-the-loop gates rather "
                    "than a free-form agent loop.",
                    "severity": "info",
                    "category": "architecture",
                },
            ],
            "risks": [
                {
                    "title": "Prompt injection / tool poisoning",
                    "detail": "Agent-reachable tools must treat external content as "
                    "adversarial: enforce Model Armor at Agent Gateway and start with a "
                    "read-only toolset.",
                    "severity": "high",
                    "category": "security",
                },
                {
                    "title": "Embedded credentials",
                    "detail": "Move datasource secrets to Secret Manager before exposing "
                    "capabilities to agents.",
                    "severity": "high",
                    "category": "security",
                },
                {
                    "title": "Non-determinism, latency and cost",
                    "detail": "Gate action-oriented tools behind human approval; route "
                    "high-volume steps to Gemini 3.5 Flash and reserve Gemini 3.1 Pro for "
                    "reasoning.",
                    "severity": "medium",
                    "category": "operations",
                },
            ],
            "migration_phases": [
                {
                    "name": "Expose as MCP tools",
                    "objective": "Publish read-only capabilities as an MCP toolset "
                    "(Cloud Run FastMCP server or Apigee MCP proxy).",
                    "effort": "M",
                },
                {
                    "name": "Orchestrate with ADK 2.0",
                    "objective": "Wrap the tools in ADK agents "
                    "(SequentialAgent/ParallelAgent) with human-in-the-loop gates.",
                    "effort": "M",
                },
                {
                    "name": "Govern",
                    "objective": "Register in Agent Registry; enforce Agent Identity, "
                    "IAM Deny/IAP, and Model Armor at Agent Gateway.",
                    "effort": "S",
                },
                {
                    "name": "Deploy to Agent Engine",
                    "objective": "Run on Vertex AI Agent Engine with OpenTelemetry "
                    "tracing and egress through Agent Gateway.",
                    "effort": "M",
                },
                {
                    "name": "Observe & federate",
                    "objective": "Stream telemetry to BigQuery Agent Analytics + Looker; "
                    "federate specialised agents over A2A v1.0.",
                    "effort": "S",
                },
            ],
            "effort_estimate": "8–12 person-weeks (re-architecture, not a lift-and-shift)",
            "recommendation": (
                "Adopt a phased agentic re-platform on Vertex AI Agent Engine: expose "
                "capabilities as MCP tools (start read-only), orchestrate with ADK 2.0 "
                "using Gemini 3, and govern every call through Agent Gateway with Agent "
                "Identity and Model Armor. Prefer the Apigee MCP proxy when the REST API "
                "is stable; choose a custom Cloud Run MCP server when you need "
                "orchestration logic. Keep humans in the loop for action-oriented tools "
                "until you have a track record."
            ),
            # Curated, validated Mermaid (raw source) — a high-quality, layered cloud
            # diagram using the Google Cloud colour palette. The agent renders it inside
            # a ```mermaid fenced block, which Agent Engine / adk web draws as a diagram.
            "diagram": (
                "flowchart LR\n"
                "  classDef svc fill:#E8F0FE,stroke:#4285F4,stroke-width:1px,color:#202124\n"
                "  classDef model fill:#FEF7E0,stroke:#F9AB00,stroke-width:1px,color:#202124\n"
                "  classDef gov fill:#FCE8E6,stroke:#EA4335,stroke-width:1px,color:#202124\n"
                "  classDef data fill:#E6F4EA,stroke:#34A853,stroke-width:1px,color:#202124\n"
                '  APP["payments-service<br/>Spring Boot · VM"]:::svc\n'
                '  subgraph EXP["1 — Expose as MCP tools"]\n'
                "    direction TB\n"
                '    CR["Cloud Run · FastMCP<br/>Path A"]:::svc\n'
                '    AP["Apigee · MCP proxy<br/>Path B"]:::svc\n'
                "  end\n"
                '  subgraph ORCH["2 — Vertex AI Agent Engine · ADK 2.0"]\n'
                "    direction TB\n"
                '    AGT["SequentialAgent / ParallelAgent<br/>+ human-in-the-loop"]:::svc\n'
                '    PRO["gemini-3.1-pro-preview<br/>reasoning"]:::model\n'
                '    FL["gemini-3.5-flash<br/>volume"]:::model\n'
                "  end\n"
                '  subgraph GOV["3 — Agent Gateway"]\n'
                "    direction TB\n"
                '    SEC["Agent Identity (mTLS+DPoP)<br/>Model Armor · IAM/IAP · Registry"]:::gov\n'
                "  end\n"
                '  OBS["BigQuery Agent Analytics<br/>+ Looker"]:::data\n'
                "  APP --> EXP\n"
                "  EXP -->|MCP| ORCH\n"
                "  GOV <-->|every call| ORCH\n"
                "  ORCH -->|OTel + audit| OBS\n"
            ),
        }

    def _generate_tests(self, p: dict[str, Any]) -> dict[str, Any]:
        framework = p.get("test_framework", "junit")
        return {
            "test_framework": framework,
            "generated_files": [
                {
                    "path": "src/test/java/com/example/OrderServiceTest.java",
                    "kind": "test",
                    "summary": "Unit tests for OrderService happy-path and validation errors.",
                },
                {
                    "path": "src/test/java/com/example/OrderControllerTest.java",
                    "kind": "test",
                    "summary": "Web-layer tests for the order endpoints.",
                },
            ],
            "recommendations": [
                "Add contract tests for the event publisher.",
                "Introduce Testcontainers for repository integration tests.",
            ],
            "warnings": [
                "Generated tests must be reviewed before commit.",
                "Mocks should align with enterprise testing standards.",
            ],
        }

    def _review_code(self, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "file_path": "src/main/java/com/example/OrderService.java",
                    "line": 42,
                    "severity": "medium",
                    "rule": "null-safety",
                    "message": "Possible NullPointerException on optional customer field.",
                    "suggestion": "Guard with Optional.ofNullable before dereferencing.",
                },
                {
                    "file_path": "src/main/resources/application.properties",
                    "line": 8,
                    "severity": "high",
                    "rule": "secrets-in-config",
                    "message": "Datasource password committed in plaintext.",
                    "suggestion": "Read from Secret Manager or an injected env var.",
                },
            ],
            "severity_summary": {"high": 1, "medium": 1, "low": 0},
            "recommendations": [
                "Resolve the high-severity secret finding before merge.",
                "Adopt the enterprise null-safety lint profile.",
            ],
            "warnings": ["Static review only; does not execute the code."],
        }


def build_backend(settings: Settings) -> WynxxBackend:
    """Construct the backend implementation selected by ``settings.mode``."""
    if settings.mode is BackendMode.REAL:
        return HttpBackend(settings)
    return StubBackend()

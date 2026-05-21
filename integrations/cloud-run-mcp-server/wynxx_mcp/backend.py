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

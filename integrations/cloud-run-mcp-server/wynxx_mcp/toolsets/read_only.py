"""Read-only toolset: analyze_repository, explain_code, generate_documentation_draft.

These tools observe and describe; they never produce changes. They carry the
``readOnlyHint`` annotation so clients (and Agent Gateway policy) can apply the
lightest approval workflow.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..backend import WynxxBackend
from ..execution import tool_execution
from ..schemas import (
    CodeExplanation,
    DocumentationDraft,
    RepositoryAnalysis,
)


def register_read_only(mcp: FastMCP, backend: WynxxBackend) -> None:
    """Register the read-only toolset on the given FastMCP server."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Analyze repository",
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def analyze_repository(
        repository_path: str,
        language: str = "java",
        depth: str = "standard",
    ) -> RepositoryAnalysis:
        """Analyze a repository and return a structured enterprise SDLC assessment.

        Args:
            repository_path: Path or identifier of the repository to analyze.
            language: Primary language of the repository (e.g. java, python, go).
            depth: Analysis depth: "shallow", "standard", or "deep".
        """
        with tool_execution("analyze_repository") as ctx:
            domain = backend.invoke(
                "analyze_repository",
                {"repository_path": repository_path, "language": language, "depth": depth},
            )
            data = {
                "repository_path": repository_path,
                "language": language,
                "depth": depth,
                **domain,
            }
            return RepositoryAnalysis(**data, metadata=ctx.metadata())

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Explain code",
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def explain_code(
        repository_path: str,
        file_path: str,
        symbol: str | None = None,
        language: str = "java",
    ) -> CodeExplanation:
        """Explain a file or symbol in plain language, with a walkthrough.

        Args:
            repository_path: Path or identifier of the repository.
            file_path: Path of the file to explain, relative to the repository.
            symbol: Optional function/class/method name to focus on.
            language: Primary language of the file.
        """
        with tool_execution("explain_code") as ctx:
            domain = backend.invoke(
                "explain_code",
                {
                    "repository_path": repository_path,
                    "file_path": file_path,
                    "symbol": symbol,
                    "language": language,
                },
            )
            data = {
                "repository_path": repository_path,
                "file_path": file_path,
                "symbol": symbol,
                "language": language,
                **domain,
            }
            return CodeExplanation(**data, metadata=ctx.metadata())

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Generate documentation draft",
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def generate_documentation_draft(
        repository_path: str,
        doc_type: str = "architecture",
        language: str = "java",
        audience: str = "engineering",
    ) -> DocumentationDraft:
        """Draft documentation (architecture, API, or onboarding) for review.

        The output is always a draft. Nothing is written to the repository.

        Args:
            repository_path: Path or identifier of the repository.
            doc_type: "architecture", "api", or "onboarding".
            language: Primary language of the repository.
            audience: Intended reader, e.g. "engineering" or "executive".
        """
        with tool_execution("generate_documentation_draft") as ctx:
            domain = backend.invoke(
                "generate_documentation_draft",
                {"repository_path": repository_path, "doc_type": doc_type, "language": language},
            )
            data = {"repository_path": repository_path, "audience": audience, **domain}
            return DocumentationDraft(**data, metadata=ctx.metadata())

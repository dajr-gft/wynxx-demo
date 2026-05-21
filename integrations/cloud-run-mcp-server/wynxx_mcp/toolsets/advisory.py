"""Advisory toolset: modernization_assessment, generate_tests, review_code.

These tools influence engineering decisions and may draft files, but they never
write to the repository or external systems — drafts are returned for human
review. They are annotated as non-read-only and non-destructive, which maps to a
stricter default approval workflow in Agent Gateway and Code Assist.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..backend import WynxxBackend
from ..execution import tool_execution
from ..schemas import (
    CodeReviewResult,
    ModernizationAssessment,
    TestGenerationResult,
)


def register_advisory(mcp: FastMCP, backend: WynxxBackend) -> None:
    """Register the advisory toolset on the given FastMCP server."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Modernization assessment",
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def modernization_assessment(
        repository_path: str,
        language: str = "java",
        target_platform: str = "cloud_run",
    ) -> ModernizationAssessment:
        """Assess modernization readiness and propose a target architecture.

        Args:
            repository_path: Path or identifier of the repository.
            language: Primary language of the repository.
            target_platform: Target runtime, e.g. "cloud_run" or "gke".
        """
        with tool_execution("modernization_assessment") as ctx:
            domain = backend.invoke(
                "modernization_assessment",
                {
                    "repository_path": repository_path,
                    "language": language,
                    "target_platform": target_platform,
                },
            )
            data = {
                "repository_path": repository_path,
                "language": language,
                "target_platform": target_platform,
                **domain,
            }
            return ModernizationAssessment(**data, metadata=ctx.metadata())

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Generate tests",
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def generate_tests(
        repository_path: str,
        language: str = "java",
        test_framework: str = "junit",
        coverage_target: int = 80,
    ) -> TestGenerationResult:
        """Draft or recommend unit and integration tests for a repository.

        Generated tests are drafts and must be reviewed before commit.

        Args:
            repository_path: Path or identifier of the repository.
            language: Primary language of the repository.
            test_framework: Target framework, e.g. "junit", "pytest", "go-test".
            coverage_target: Desired coverage percentage (0–100).
        """
        with tool_execution("generate_tests") as ctx:
            domain = backend.invoke(
                "generate_tests",
                {
                    "repository_path": repository_path,
                    "language": language,
                    "test_framework": test_framework,
                    "coverage_target": coverage_target,
                },
            )
            data = {
                "repository_path": repository_path,
                "language": language,
                "coverage_target": coverage_target,
                **domain,
            }
            return TestGenerationResult(**data, metadata=ctx.metadata())

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Review code",
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        )
    )
    def review_code(
        repository_path: str,
        file_path: str | None = None,
        ruleset: str = "enterprise-default",
        language: str = "java",
    ) -> CodeReviewResult:
        """Perform a static, advisory code review against a ruleset.

        Args:
            repository_path: Path or identifier of the repository.
            file_path: Optional single file to scope the review.
            ruleset: Named ruleset, e.g. "enterprise-default" or "security".
            language: Primary language of the repository.
        """
        with tool_execution("review_code") as ctx:
            domain = backend.invoke(
                "review_code",
                {
                    "repository_path": repository_path,
                    "file_path": file_path,
                    "ruleset": ruleset,
                    "language": language,
                },
            )
            data = {
                "repository_path": repository_path,
                "language": language,
                "ruleset": ruleset,
                **domain,
            }
            return CodeReviewResult(**data, metadata=ctx.metadata())

"""Typed input/output contracts for the Wynxx MCP tools.

These models *are* the MCP contract. FastMCP turns the parameter signatures
into JSON input schemas and these return models into JSON output schemas, so
keeping them precise and well-described is a governance activity, not just a
typing nicety.

Every tool output embeds an :class:`ExecutionMetadata` block so the result is
traceable end-to-end — the same shape consumed by ``integrations/bigquery-observability``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelArmorVerdict(StrEnum):
    """Placeholder for the verdict Agent Gateway / Model Armor attaches.

    The MCP server itself does not run Model Armor; it records the verdict it
    was handed so the execution record is complete.
    """

    ALLOW = "allow"
    BLOCK = "block"
    NOT_EVALUATED = "not_evaluated"


# ---------------------------------------------------------------------------
# Execution metadata (traceability)
# ---------------------------------------------------------------------------


class ExecutionMetadata(BaseModel):
    """Traceable execution record embedded in every tool response."""

    execution_id: str = Field(description="Unique id for this tool invocation.")
    tool: str = Field(description="Fully-qualified tool name, e.g. wynxx.analyze_repository.")
    mcp_server: str = Field(description="Logical MCP server id, e.g. wynxx-sdlc.")
    backend_mode: str = Field(description="stub or real.")
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    duration_ms: int = Field(ge=0, description="Wall-clock execution time in milliseconds.")
    model_armor_verdict: ModelArmorVerdict = ModelArmorVerdict.NOT_EVALUATED
    trace_id: str = Field(description="OpenTelemetry trace id (or a generated correlation id).")
    timestamp: datetime = Field(description="UTC completion time, ISO 8601.")


# ---------------------------------------------------------------------------
# Read-only toolset — outputs
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    """A single, severity-tagged observation about a repository."""

    title: str
    detail: str
    severity: Severity = Severity.INFO
    category: str = Field(default="general", description="e.g. architecture, testing, security.")


class Artifact(BaseModel):
    """A reference to a produced or referenced artifact (never the raw bytes)."""

    name: str
    kind: str = Field(description="e.g. document, test-file, diagram, report.")
    uri: str | None = Field(default=None, description="Optional storage URI (gs://, https://).")


class RepositoryAnalysis(BaseModel):
    """Output of ``analyze_repository``."""

    repository_path: str
    language: str
    depth: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    risks: list[Finding] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: ExecutionMetadata


class CodeExplanation(BaseModel):
    """Output of ``explain_code``."""

    repository_path: str
    file_path: str
    symbol: str | None = None
    language: str
    summary: str
    walkthrough: list[str] = Field(default_factory=list)
    key_components: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    complexity: Severity = Field(
        default=Severity.LOW, description="Relative reasoning complexity of the code."
    )
    metadata: ExecutionMetadata


class DocumentationSection(BaseModel):
    heading: str
    content: str


class DocumentationDraft(BaseModel):
    """Output of ``generate_documentation_draft``."""

    repository_path: str
    doc_type: str
    title: str
    audience: str
    format: str = "markdown"
    sections: list[DocumentationSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    metadata: ExecutionMetadata


# ---------------------------------------------------------------------------
# Advisory toolset — outputs
# ---------------------------------------------------------------------------


class MigrationPhase(BaseModel):
    name: str
    objective: str
    effort: str = Field(description="Rough effort band, e.g. S / M / L or person-weeks.")


class ModernizationAssessment(BaseModel):
    """Output of ``modernization_assessment``."""

    repository_path: str
    language: str
    target_platform: str
    current_state: str
    target_architecture: str
    findings: list[Finding] = Field(default_factory=list)
    risks: list[Finding] = Field(default_factory=list)
    migration_phases: list[MigrationPhase] = Field(default_factory=list)
    effort_estimate: str
    recommendation: str
    diagram: str | None = Field(
        default=None,
        description="Mermaid source for the target-architecture diagram (when available).",
    )
    metadata: ExecutionMetadata


class GeneratedFile(BaseModel):
    """A drafted file reference. Drafts are never committed automatically."""

    path: str
    kind: str = Field(default="test", description="e.g. test, fixture, config.")
    summary: str


class TestGenerationResult(BaseModel):
    """Output of ``generate_tests``."""

    repository_path: str
    language: str
    test_framework: str
    coverage_target: int = Field(ge=0, le=100)
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    metadata: ExecutionMetadata


class ReviewFinding(BaseModel):
    file_path: str
    line: int | None = None
    severity: Severity = Severity.LOW
    rule: str
    message: str
    suggestion: str | None = None


class CodeReviewResult(BaseModel):
    """Output of ``review_code``."""

    repository_path: str
    language: str
    ruleset: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    severity_summary: dict[str, int] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    metadata: ExecutionMetadata
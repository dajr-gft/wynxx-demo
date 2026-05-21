# Example SDLC package

This is the **output** of the end-to-end workflow from the article — the bundle
produced when a developer asks Gemini Code Assist (or the ADK workflow) to
*"analyze this repository, identify missing tests, generate an architecture
summary, and recommend a modernization path for Google Cloud."*

The subject is a fictional `payments-service` (Spring Boot), matching the stub
findings in [`../cloud-run-mcp-server/`](../cloud-run-mcp-server/) and
[`../adk-agent-workflow/`](../adk-agent-workflow/).

```
sdlc-package/
├── architecture-summary.md       # doc_writer
├── api-overview.md               # doc_writer
├── test-recommendations.md       # test_strategist
├── modernization-assessment.md   # modernization_advisor
├── migration-plan-gcp.md         # modernization_advisor
└── execution-metadata.json       # observability record for the run
```

That is the difference between a coding assistant and an SDLC agent stack: the
developer gets acceleration, the architect gets consistency, QA gets test
recommendations, the platform team gets migration signals, security gets
auditability, and the executive team gets metrics.

> These artifacts are illustrative samples. In a real run they are generated
> from your actual repository and reviewed at the human-in-the-loop gate before
> being written.

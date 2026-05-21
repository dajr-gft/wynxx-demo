# Path A — Custom MCP server on Cloud Run

A complete, production-shaped implementation of the article's **Path A**: a
custom [FastMCP](https://github.com/modelcontextprotocol/python-sdk) server that
exposes a Wynxx-style enterprise SDLC platform as MCP tools, deployable to Cloud
Run behind Agent Gateway.

This path is the right choice when you need custom logic, tool-call
orchestration that doesn't map cleanly to REST, or non-HTTP integrations
(queues, gRPC, internal protocols). If your platform already exposes REST, see
[Path B](../apigee-mcp-bridge/).

## What's here

```
cloud-run-mcp-server/
├── server.py                 # Cloud Run entrypoint (the article's server.py)
├── Dockerfile                # rootless, multi-stage image
├── deploy.sh                 # gcloud run deploy --no-allow-unauthenticated
├── requirements.txt          # runtime deps  (+ requirements-otel.txt)
├── pyproject.toml            # packaging, pytest, ruff
├── .env.example              # configuration reference
├── wynxx_mcp/
│   ├── server.py             # build_server(): FastMCP + toolsets
│   ├── config.py             # WYNXX_* settings, stub/real switch
│   ├── schemas.py            # the 6-tool contract as Pydantic models
│   ├── backend.py            # StubBackend | HttpBackend (the integration seam)
│   ├── execution.py          # per-call trace + timing + audit metadata
│   ├── observability.py      # structured logging + optional OpenTelemetry
│   └── toolsets/
│       ├── read_only.py      # analyze_repository, explain_code, generate_documentation_draft
│       └── advisory.py       # modernization_assessment, generate_tests, review_code
└── tests/                    # pytest suite
```

## The tool contract

Six tools across two toolsets, matching the article's MCP contract. Every tool
returns a **typed Pydantic model**, so FastMCP automatically publishes a JSON
output schema and emits structured content — and every result embeds an
`ExecutionMetadata` block for traceability.

| Toolset | Tool | Returns |
|---|---|---|
| read-only | `analyze_repository` | `RepositoryAnalysis` |
| read-only | `explain_code` | `CodeExplanation` |
| read-only | `generate_documentation_draft` | `DocumentationDraft` |
| advisory | `modernization_assessment` | `ModernizationAssessment` |
| advisory | `generate_tests` | `TestGenerationResult` |
| advisory | `review_code` | `CodeReviewResult` |

Read-only tools carry the `readOnlyHint` annotation; advisory tools are marked
non-read-only and non-destructive. Agent Gateway and Code Assist use these hints
to pick the right default approval workflow.

## Run it locally

```bash
cd integrations/cloud-run-mcp-server
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Offline by default — deterministic stub responses, no cloud needed.
python server.py
# → MCP served over streamable HTTP at http://localhost:8080/mcp
```

Point any MCP client at `http://localhost:8080/mcp`. For Gemini CLI, see
[`../gemini-surfaces/`](../gemini-surfaces/).

### Switch to a live backend

```bash
export WYNXX_MODE=real
export WYNXX_BACKEND_URL=https://34.71.69.43.nip.io   # e.g. the ../../.gemini instance
export WYNXX_BACKEND_TOKEN=...                          # optional
python server.py
```

The contract is identical in both modes — only `backend.py` changes behaviour.

## Test, lint

```bash
pip install -e ".[dev]"
pytest          # unit tests for backend, schemas, execution, and registration
ruff check .
```

## Deploy to Cloud Run

```bash
PROJECT_ID=my-project ./deploy.sh
```

This runs `gcloud run deploy --no-allow-unauthenticated` with a dedicated
service account. **Authentication is not optional** — the service is never
public; Agent Gateway reaches it over an authenticated channel. After deploy,
register the server with [`../agent-gateway-governance/register-mcp-server.sh`](../agent-gateway-governance/).

The server runs with `stateless_http=True` + `json_response=True`, so each tool
call is a self-contained request/response with no per-session server state —
exactly what Cloud Run autoscaling needs (no instance affinity).

## Observability

Every tool call emits a single JSON log line (the `ExecutionMetadata` record),
collected by Cloud Logging. Set `WYNXX_ENABLE_OTEL=true` and install
`requirements-otel.txt` to additionally export OpenTelemetry spans. The record
shape matches [`../bigquery-observability/`](../bigquery-observability/).

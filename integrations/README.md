# Reference integrations — *Enterprise SDLC Agents on Google Cloud*

Complete, runnable companions to the article
**[After Next '26: A Reference Architecture for Enterprise SDLC Agents on Google Cloud](../docs/reference-architecture.md)**.

Every snippet in the article is expanded here into a production-grade,
self-contained example. The article keeps the code minimal so the
architecture stays visible; this directory keeps the code *complete* so you
can actually run it. Each subdirectory is named after the Google Cloud product
it integrates Wynxx with.

## How the integrations map to the article

| Article section | Directory | GCP product | What it contains |
|---|---|---|---|
| *Designing the MCP contract* | [`cloud-run-mcp-server/`](cloud-run-mcp-server/) | Cloud Run | The full 6-tool contract (read-only + advisory toolsets) as typed schemas |
| *Path A — Custom MCP server on Cloud Run* | [`cloud-run-mcp-server/`](cloud-run-mcp-server/) | Cloud Run | FastMCP server, Dockerfile, tests, Cloud Run deploy |
| *Path B — Apigee as MCP bridge* | [`apigee-mcp-bridge/`](apigee-mcp-bridge/) | Apigee | Complete OpenAPI 3.1 spec + MCP-proxy deploy script |
| *Wrapping it with Agent Gateway* | [`agent-gateway-governance/`](agent-gateway-governance/) | Agent Gateway / Registry | Agent Registry registration + per-agent egress grant scripts |
| *ADK 2.0 — agentic orchestration* | [`adk-agent-workflow/`](adk-agent-workflow/) | ADK 2.0 / Agent Engine | Graph-based fan-out/fan-in workflow + human-in-the-loop |
| *The three consumer surfaces* | [`gemini-surfaces/`](gemini-surfaces/) | Gemini CLI / Code Assist | Gemini CLI & Gemini Code Assist `settings.json` |
| *Observability* | [`bigquery-observability/`](bigquery-observability/) | BigQuery | Execution-record JSON Schema + BigQuery sink |
| *An end-to-end enterprise workflow* | [`sdlc-package/`](sdlc-package/) | — | Example SDLC artifact package produced by the workflow |

## Design choices shared across all integrations

These integrations were built to the same six principles the article closes with:

1. **Read-only first.** Tools are split into a `read-only` toolset and an
   `advisory` toolset; nothing writes to your repository or external systems.
2. **Humans in control.** The ADK workflow gates every artifact behind a
   `human_in_the_loop` node.
3. **Structured outputs.** Every tool returns a typed Pydantic model, so the
   MCP layer emits a JSON output schema automatically.
4. **Every execution is logged.** Each tool call produces an
   `ExecutionMetadata` record matching the observability schema.
5. **Local vs. enterprise context is explicit.** A `WYNXX_MODE` switch selects
   a self-contained `stub` backend or a `real` backend — never silently.
6. **Built for an operating model.** Identity, governance, and registry are
   first-class scripts, not afterthoughts.

## The `stub` vs `real` backend switch

Each Python integration runs **offline by default** against a deterministic stub
backend, so you can explore the architecture without any cloud dependency:

```bash
export WYNXX_MODE=stub      # default — no network, deterministic responses
```

To point the same code at a live Wynxx instance (for example the one wired into
[`../.gemini/settings.json`](../.gemini/settings.json)), flip the switch and
provide the endpoint:

```bash
export WYNXX_MODE=real
export WYNXX_BACKEND_URL=https://34.71.69.43.nip.io
export WYNXX_BACKEND_TOKEN=...      # optional bearer/ID token
```

The backend abstraction ([`backend.py`](cloud-run-mcp-server/wynxx_mcp/backend.py))
is the single seam where real integration plugs in — everything else stays the
same.

## Prerequisites

- Python 3.12+
- `gcloud` CLI (for the Cloud Run / Agent Registry integrations)
- An MCP-capable client (Gemini CLI, Gemini Code Assist, or any compliant client)
  to exercise the server interactively

See each subdirectory's `README.md` for step-by-step instructions.

---

> These are reference implementations. The stub responses are illustrative; the
> contracts, schemas, governance scripts, and deployment topology are the parts
> meant to be reused.
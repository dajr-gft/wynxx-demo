# Wynxx × Google Cloud — reference integrations

Reference implementations for exposing **[Wynxx](https://www.gft.com)** (GFT's
GenAI platform for enterprise software delivery) as **MCP** and integrating it
across the post-Cloud Next '26 Google Cloud agent stack — Cloud Run, Apigee,
ADK 2.0 / Agent Engine, Agent Gateway, BigQuery, and the Gemini surfaces.

Each directory under [`integrations/`](integrations/) is named after the Google
Cloud product it connects Wynxx to, runs **offline by default** against a
deterministic stub backend, and maps 1:1 to a section of the reference
architecture article in [`docs/`](docs/reference-architecture.md).

![Enterprise SDLC agent stack on Google Cloud (post Next '26)](docs/diagrams/architecture.png)

## Integration matrix

| Google Cloud product | Integration | What it shows |
|---|---|---|
| **Cloud Run** | [`integrations/cloud-run-mcp-server/`](integrations/cloud-run-mcp-server/) | Custom FastMCP server (the 6-tool contract) + Dockerfile, tests, authenticated Cloud Run deploy — *Path A* |
| **Apigee** | [`integrations/apigee-mcp-bridge/`](integrations/apigee-mcp-bridge/) | Existing REST API published as governed MCP tools via an MCP proxy (OpenAPI 3.1) — *Path B* |
| **Agent Gateway / Registry** | [`integrations/agent-gateway-governance/`](integrations/agent-gateway-governance/) | Agent Registry registration + per-agent egress grant (Agent Identity, IAM, Model Armor) |
| **ADK 2.0 / Agent Engine** | [`integrations/adk-agent-workflow/`](integrations/adk-agent-workflow/) | Graph-based fan-out/fan-in SDLC workflow with a human-in-the-loop gate |
| **Gemini CLI / Code Assist** | [`integrations/gemini-surfaces/`](integrations/gemini-surfaces/) | Client `settings.json` for the developer-facing consumer surfaces |
| **BigQuery** | [`integrations/bigquery-observability/`](integrations/bigquery-observability/) | Execution-record JSON Schema + partitioned/clustered BigQuery sink + analytics SQL |
| *(output sample)* | [`integrations/sdlc-package/`](integrations/sdlc-package/) | The SDLC artifact bundle produced end-to-end by the workflow |

## Repository layout

```
.
├── docs/
│   ├── reference-architecture.md     # the full article this repo implements
│   └── diagrams/                     # architecture + SDLC-iceberg diagrams
├── integrations/                     # one directory per Google Cloud product
│   ├── cloud-run-mcp-server/         # Cloud Run — custom MCP server (Path A)
│   ├── apigee-mcp-bridge/            # Apigee — MCP proxy over existing REST (Path B)
│   ├── agent-gateway-governance/     # Agent Gateway / Identity / Registry
│   ├── adk-agent-workflow/           # ADK 2.0 graph workflow on Agent Engine
│   ├── gemini-surfaces/              # Gemini CLI & Code Assist client config
│   ├── bigquery-observability/       # execution records → BigQuery → Looker
│   └── sdlc-package/                 # example output bundle
├── .gemini/settings.json             # sample Gemini CLI config (live Wynxx instance)
└── .github/workflows/ci.yml          # lint, tests, OpenAPI + JSON-Schema validation
```

## Quickstart

Everything runs locally with no cloud account — the stub backend returns
deterministic responses so the architecture is explorable offline.

```bash
# 1. Custom MCP server on Cloud Run (Path A)
cd integrations/cloud-run-mcp-server
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py            # MCP over streamable HTTP at http://localhost:8080/mcp

# 2. ADK 2.0 SDLC workflow (offline graph demo)
cd ../adk-agent-workflow
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m sdlc_workflow
```

See [`integrations/README.md`](integrations/README.md) and each subdirectory's
`README.md` for full instructions, and switch any Python integration to a live
Wynxx instance with `WYNXX_MODE=real`.

## The two exposure paths

Both land behind the same Agent Gateway and present an identical 6-tool MCP
contract; many enterprises run both.

- **Path A — Cloud Run MCP server.** Right when you need custom logic,
  orchestration that doesn't map to REST, or non-HTTP integrations.
- **Path B — Apigee MCP bridge.** Right when your platform already exposes
  REST: publish it as MCP tools with no server to write or operate.

## Prerequisites

- Python 3.12+
- `gcloud` CLI (only for the Cloud Run / Agent Registry deploys)
- An MCP-capable client (Gemini CLI, Gemini Code Assist, or any compliant client)

## Disclaimer

These are reference implementations, not a production-ready product. Stub
responses are illustrative; the contracts, schemas, governance scripts, and
deployment topology are the parts meant to be reused. The post-Next '26 Google
Cloud APIs referenced here reflect the announced Agent Platform surface —
confirm exact flags against your `gcloud` version.

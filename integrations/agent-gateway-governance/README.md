# Governance — Agent Gateway, Agent Identity, Agent Registry

Either path ([A](../cloud-run-mcp-server/) or [B](../apigee-mcp-bridge/)) lands behind
**Agent Gateway** — the part of the stack that didn't exist before Next '26 and
that matters most for regulated industries. This directory contains the scripts
that put a Wynxx MCP server under that governance plane.

## What's here

```
agent-gateway-governance/
├── register-mcp-server.sh           # add the server to Agent Registry
├── scripts/
│   └── grant_agent_mcp_egress.sh    # bind one agent identity -> one MCP server
└── README.md
```

## The governance pipeline (in order)

Agent Gateway applies this pipeline to every call, in both **ingress**
(client/agent → your tools) and **egress** (your agents → anywhere) modes:

1. **Agent Identity** — validate the mTLS-secured persona of the calling agent.
2. **IAM Deny policies + IAP** — enforce least-privilege at runtime against the
   registered resource path in Agent Registry.
3. **Model Armor** — inspect request and response for prompt injection, tool
   poisoning, and sensitive-data exfiltration.
4. **Audit + tracing** — emit Cloud Audit Logs and OpenTelemetry spans for the
   full call chain (see [`../bigquery-observability/`](../bigquery-observability/)).

## Step 1 — register the server

```bash
PROJECT_ID=my-project \
ENDPOINT_URL=https://wynxx-mcp-server-xxxxx.run.app/mcp \
./register-mcp-server.sh
```

`ENDPOINT_URL` is the `.../mcp` endpoint of whichever path you deployed — the
Cloud Run service URL (Path A) or the Apigee env-group host (Path B).

## Step 2 — grant a named agent egress (the CISO-review command)

```bash
./scripts/grant_agent_mcp_egress.sh \
  --mcp wynxx-sdlc \
  --agent-id sdlc-orchestrator-agent
```

This is the command that makes the system survive a security review: an explicit
grant from **one named Agent Identity** to **one named MCP server** —
recorded, auditable, and revocable. Revoke with `--revoke`.

## Pre- vs post-Next '26 controls

| Concern | Pre-Next '26 (DIY) | Post-Next '26 (platform) |
|---|---|---|
| Agent authentication | Static bearer tokens | **Agent Identity** (mTLS + DPoP) |
| Tool authorization | App-level RBAC | **Agent Gateway** + **IAM Deny** + **IAP** |
| Prompt injection / tool poisoning | DIY input filtering | **Model Armor** at runtime |
| Sensitive data in tool calls | App-level redaction | **Cloud DLP** via Apigee / Gateway |
| Tool discovery | Hand-maintained registries | **Agent Registry** + **Apigee API hub** |
| Tool execution audit | Custom logging | **Cloud Audit Logs** + **OpenTelemetry** |
| Agent threat detection | Manual SOC rules | **Security Command Center** |

## Tool classification drives policy

The toolset split in the MCP server isn't cosmetic — it maps to different
Agent Gateway policies and Code Assist approval defaults:

- **Read-only** (`analyze_repository`, `explain_code`, `generate_documentation_draft`)
  — easiest to approve.
- **Advisory** (`modernization_assessment`, `generate_tests`, `review_code`)
  — influence engineering decisions; stricter approval.
- **Action-oriented** (not shipped in this reference: `update_files`,
  `create_jira_stories`, `commit_pr`) — change artifacts or external systems;
  always human-gated.

> The `gcloud agent-platform` commands reflect the post-Next '26 Agent Platform
> surface. Treat them as the canonical shape of the governance workflow; confirm
> exact flags against your `gcloud` version.

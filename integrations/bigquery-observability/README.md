# Observability — turning agent usage into engineering intelligence

Post-Next '26, most of this telemetry comes for free: ADK emits OpenTelemetry
traces by default, Agent Gateway adds structured Cloud Audit Logs for every tool
call, and the **BigQuery Agent Analytics plugin** logs detailed interactions
from ADK and LangGraph directly to BigQuery. This directory defines the record
schema and the BigQuery sink that make it queryable.

## What's here

```
bigquery-observability/
├── execution-metadata.example.json   # one execution record (the article's record)
├── execution-metadata.schema.json    # JSON Schema (draft 2020-12) for that record
└── bigquery/
    ├── schema.json                   # BigQuery table schema
    ├── create_table.sh               # partitioned + clustered sink
    └── analytics.sql                 # the leadership / engineering-intelligence queries
```

## The execution record

Every tool call produces one record. The Path A MCP server emits the
**tool-level subset** (see `wynxx_mcp.schemas.ExecutionMetadata`); Agent Gateway
and the orchestration layer **enrich** it with identity, tenant, and artifact
context before it lands in BigQuery.

```json
{
  "execution_id": "exec-12345",
  "agent_identity": "sdlc-orchestrator-agent",
  "user_id": "user@example.com",
  "tenant_id": "banking-client-a",
  "repository": "payments-service",
  "tool": "wynxx.analyze_repository",
  "mcp_server": "wynxx-sdlc",
  "status": "success",
  "duration_ms": 12840,
  "model_armor_verdict": "allow",
  "artifacts": ["architecture-summary.md", "modernization-assessment.md"],
  "trace_id": "00-a1b2c3d4...",
  "timestamp": "2026-05-19T10:30:00Z"
}
```

Validate any record against the schema:

```bash
pip install check-jsonschema
check-jsonschema --schemafile execution-metadata.schema.json execution-metadata.example.json
```

## Stand up the BigQuery sink

```bash
PROJECT_ID=my-project ./bigquery/create_table.sh
```

The table is **partitioned by day** on `timestamp` and **clustered** by
`tenant_id, tool` — the access pattern for high-volume agent telemetry, so
dashboards stay cheap and fast.

## From "AI usage" to leadership signal

Run `bigquery/analytics.sql` (or wire it into Looker) and the conversation
changes from *"developers are using AI"* to:

```text
42 repositories analyzed
318 test files drafted
96 documentation artifacts generated
17 applications identified as modernization candidates
12 high-risk dependency patterns detected
 2 Model Armor blocks on suspicious prompt patterns
```

That is how AI developer tooling stops being a productivity story and becomes an
**engineering intelligence platform**.

# Consumer surfaces — Gemini CLI & Gemini Code Assist

The same Wynxx MCP exposure is reachable from every surface. These are the
client configurations for the two developer-facing ones; the ADK and Gemini
Enterprise surfaces are covered in [`../adk-agent-workflow/`](../adk-agent-workflow/).

## What's here

```
gemini-surfaces/
├── gemini-cli.settings.json          # ~/.gemini/settings.json (read-only rollout)
└── gemini-code-assist.settings.json  # IDE Code Assist (full toolset, Agent Mode)
```

## 1. Gemini CLI — terminal entry point

Merge `gemini-cli.settings.json` into `~/.gemini/settings.json`.

```jsonc
{
  "mcpServers": {
    "wynxx": {
      "httpUrl": "https://wynxx-mcp-server-xxxxx.run.app/mcp",
      "authProviderType": "google_credentials",
      "oauth": { "scopes": ["https://www.googleapis.com/auth/cloud-platform"] },
      "timeout": 300000,
      "trust": false,
      "includeTools": ["analyze_repository", "explain_code", "generate_documentation_draft"]
    }
  }
}
```

- `authProviderType: "google_credentials"` is the post-Next '26 default — Gemini
  CLI authenticates with Application Default Credentials, so there is **no static
  bearer token to rotate**.
- `includeTools` starts with the **read-only toolset** only — the "start
  read-only" principle. Add advisory tools deliberately once you have a track
  record.
- `trust: false` keeps tool calls behind explicit approval.

Then, from a repository:

```text
> Use Wynxx to analyze this repository and propose a modernization path to
  Google Cloud.
```

Gemini CLI discovers the tools, calls `wynxx.analyze_repository`, and returns
structured findings.

> Note: the repo's own [`../../.gemini/settings.json`](../../.gemini/settings.json)
> uses the **stdio** form (`npx @wynxx/mcp …`) against a live Wynxx instance.
> This file shows the **HTTP** form against the Cloud Run / Apigee endpoint
> from Path A / Path B. Both are valid; pick the transport that matches your
> deployment.

## 2. Gemini Code Assist — IDE entry point

The same `mcpServers` block lives in the Code Assist configuration. With **Agent
Mode** enabled, intent like *"review this service, identify missing tests,
generate API docs"* is routed to the Wynxx tools, with human approval required
for any action that writes files.

`gemini-code-assist.settings.json` includes the **full toolset** because the IDE
is where advisory tools are most useful — but keep `trust: false` for the first
enterprise rollout. When tools can inspect code, generate files, or interact
with external systems, developers should approve invocations. In regulated
environments, human approval is not friction — it is part of responsible
automation.

## Tool classification → approval defaults

| Toolset | Tools | Default approval |
|---|---|---|
| read-only | `analyze_repository`, `explain_code`, `generate_documentation_draft` | lightweight |
| advisory | `modernization_assessment`, `generate_tests`, `review_code` | explicit, per-call |

These map to the same classification Agent Gateway enforces server-side — see
[`../agent-gateway-governance/`](../agent-gateway-governance/).

# Path B — Apigee as MCP bridge

The article's **post-Next '26 path**: if your SDLC platform already exposes REST
APIs, Apigee can publish them as governed MCP tools through an **MCP proxy** —
no MCP server to write or operate.

This directory contains the complete OpenAPI 3.1 spec that drives that proxy,
plus a deploy script and the Console steps.

## What's here

```
apigee-mcp-bridge/
├── wynxx-openapi.yaml     # complete OpenAPI 3.1 spec — the MCP tool contract
├── deploy-apigee.sh       # create + deploy the MCP proxy via apigeecli
└── README.md
```

## How the spec becomes MCP tools

When you create an MCP proxy and attach `wynxx-openapi.yaml`, Apigee uses each
operation's `operationId` as a tool name and its request/response schemas as the
tool's input/output schema. The six operations map 1:1 to the Path A tools, so a
client sees an identical contract no matter which path serves it:

| `operationId` (MCP tool) | Method + path | Toolset |
|---|---|---|
| `analyze_repository` | `POST /analyze` | read-only |
| `explain_code` | `POST /explain` | read-only |
| `generate_documentation_draft` | `POST /generate-documentation` | read-only |
| `modernization_assessment` | `POST /modernization-assessment` | advisory |
| `generate_tests` | `POST /generate-tests` | advisory |
| `review_code` | `POST /review` | advisory |

## Deploy

### Option 1 — script

```bash
PROJECT_ID=my-project APIGEE_ENV=eval APIGEE_ENVGROUP=eval-group ./deploy-apigee.sh
```

### Option 2 — Console (the documented mechanics)

1. In Apigee, **create a new proxy** of type **MCP** in your environment group.
2. Set the **basepath** to `/mcp`.
3. Point the **target URL** to `mcp.apigee.internal`.
4. **Attach** `wynxx-openapi.yaml` — Apigee derives the tools list from its
   operations.
5. **Deploy.** The proxy is automatically registered in **Apigee API hub**.

Once live, any compliant MCP client — Gemini CLI, Code Assist, ADK, Claude,
ChatGPT, VS Code — can call `tools/list` against
`https://<env-group-host>/mcp` and discover the tools, with Apigee handling
transcoding and protocol mediation.

## Validate the spec locally

```bash
pip install openapi-spec-validator
openapi-spec-validator wynxx-openapi.yaml
```

(The CI workflow runs this on every change.)

## What you get for free with Path B

- **30+ Apigee policies** for authn/authz, rate limiting, quotas, and DLP.
- **OAuth 2.1 / OIDC** out of the box (see the `oauth2` security scheme).
- **Apigee API hub** as a central, semantically-searchable tool catalog.
- **Cloud DLP** integration for sensitive data passing through the tool.
- **Model Armor** integration against prompt injection and jailbreaking.
- **Apigee Analytics** to monitor MCP tool usage by client.

## Path A or Path B?

Not dogmatic — many deployments use both: Apigee for stable, production REST
APIs; a custom [Cloud Run MCP server](../cloud-run-mcp-server/) for orchestrated
workflows that need internal reasoning before returning. Both coexist behind the
same [Agent Gateway](../agent-gateway-governance/).

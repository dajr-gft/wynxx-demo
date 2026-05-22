# Testing ADK against the **real** Wynxx product — setup notes

This documents the extra, non-obvious configuration needed to drive the **real
Wynxx product** from ADK (not the repo's stub/HTTP reference server). It was
validated end-to-end on 2026-05-21 against instance `34.71.69.43.nip.io`.

> **Key architecture point.** The real product's MCP surface is the **native
> `@wynxx/mcp` npm package** (stdio, OAuth) — the same one wired into
> [`../../.gemini/settings.json`](../../.gemini/settings.json). The repo's
> [`cloud-run-mcp-server`](../cloud-run-mcp-server/) is a *reference* server whose
> `HttpBackend` speaks a generic REST contract (`POST /analyze`, …), **not** the
> real Wynxx Keycloak + async-job protocol. So a real test connects ADK directly
> to `@wynxx/mcp` over **stdio**, not to the repo's HTTP server.

## What was validated

| Test | Script | Result |
|---|---|---|
| ADK ↔ real Wynxx wire (discovery + read-only invocation) | [`integration_real_native.py`](integration_real_native.py) | ✅ 38 real tools; `authenticate` + `list_llms` OK |
| Catalogs + job-tool input schemas | [`explore_real.py`](explore_real.py) | ✅ projects, jobs, prompts, audiences |
| Real job end-to-end (Code Documenter) | [`run_real_job.py`](run_real_job.py) | ⚠️ job submitted (real `jobId`), `CompletedWithErrors` — see [known issue](#known-issue-server-side-vertex-iam) |
| LLM-driven ADK agent (Gemini reasoning + real tools) | [`agent_llm_real.py`](agent_llm_real.py) | ✅ Gemini 3.5 Flash (Vertex global) calls `list_projects`/`list_llms` |
| Full workflow (SequentialAgent + ParallelAgent + HITL) | [`run_workflow_real.py`](run_workflow_real.py) | ✅ analyze → 3 parallel drafts → human-gated publish, Gemini 3 + Wynxx tools |

## Prerequisites

- Python 3.12+ with the **real** deps installed in the venv:
  ```bash
  pip install -r requirements.txt -r requirements-real.txt
  ```
  `requirements-real.txt` now pins **`mcp`** explicitly — `google-adk` did not pull
  the MCP client library in transitively, and `McpToolset` fails without it
  (`ModuleNotFoundError: No module named 'mcp'`).
- **Node.js / npx** (to run the native `@wynxx/mcp` package).
- **npm authenticated to the GFT Azure Artifacts feed** (the `@wynxx` scope is
  private). If `npm view @wynxx/mcp version` fails with 401, authenticate the feed
  (the global `~/.npmrc` token is reused).

## 1. Native `@wynxx/mcp` over ADK stdio

ADK launches the package as a stdio subprocess. Two things are required beyond
the connection params:

- **Point the `@wynxx` scope at the private feed** so `npx` can resolve it. The
  scripts inject this into the subprocess env (the feed *auth* still comes from
  your global `~/.npmrc`):
  ```python
  env["npm_config_@wynxx:registry"] = (
      "https://pkgs.dev.azure.com/gft-assets/ai-impact-feed/"
      "_packaging/ai-impact-feed/npm/registry/"
  )
  ```
- **OAuth login.** On first connect `@wynxx/mcp` opens a browser (callback on
  port 8765) for Keycloak login. Complete it once; the token is cached for
  subsequent runs.

Connection (see any of the scripts):
```python
StdioConnectionParams(
    server_params=StdioServerParameters(
        command="npx",  # resolved via shutil.which on Windows -> npx.cmd
        args=["-y", "@wynxx/mcp", "--instance", "34.71.69.43.nip.io", "--language", "pt-BR"],
        env=env,
    ),
    timeout=600,
)
```

Run the discovery probe:
```bash
.venv/Scripts/python.exe integration_real_native.py
```

## 2. `gcloud` was broken in the shell — fix `CLOUDSDK_PYTHON`

`gcloud` failed with *"Python was not found …"* (the Windows Store Python stub),
because `CLOUDSDK_PYTHON` was unset and `python` resolved to the stub. Point it at
the SDK's **bundled** Python (persisted at user level so new shells inherit it):

```powershell
$bundled = 'C:\Users\dajr\AppData\Local\GoogleCloudSDK\google-cloud-sdk\platform\bundledpython\python.exe'
[Environment]::SetEnvironmentVariable('CLOUDSDK_PYTHON', $bundled, 'User')
$env:CLOUDSDK_PYTHON = $bundled   # current shell
```

> Already-open shells (including Claude Code's) won't pick up the persisted value
> until restarted — set `$env:CLOUDSDK_PYTHON` inline for the current session.

## 3. Vertex AI for LLM-driven runs (`agent_llm_real.py`)

The ADK agent's *own* reasoning needs a Gemini model. We used **Vertex AI**:

```powershell
gcloud auth application-default login                              # ADC (browser)
gcloud auth application-default set-quota-project wynxx-tests      # quota project
```

Then the env the agent sets (Vertex AI API must be enabled on the project and the
user needs `roles/aiplatform.user`):

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=wynxx-tests
GOOGLE_CLOUD_LOCATION=global   # Gemini 3 models are served on the global endpoint
```

- **Models.** Real mode uses **`gemini-3.1-pro-preview`** (reasoning) and
  **`gemini-3.5-flash`** (volume). Both resolve **only on the Vertex `global`
  endpoint** (they 404 in regional endpoints like `us-central1`), so
  `GOOGLE_CLOUD_LOCATION=global` is required. The bare aliases
  `gemini-3-pro` / `gemini-3-flash` do **not** resolve — use the exact ids above.

Run the LLM-driven agent (single `LlmAgent` over the native MCP), or the full
`SequentialAgent`/`ParallelAgent` workflow against the repo's HTTP MCP server:
```bash
.venv/Scripts/python.exe agent_llm_real.py        # native @wynxx/mcp (stdio)

# full workflow: start the repo MCP server first, then drive the graph
( cd ../cloud-run-mcp-server && WYNXX_MODE=stub python server.py & )
.venv/Scripts/python.exe run_workflow_real.py     # SequentialAgent + ParallelAgent
```

## Known issue: server-side Vertex IAM

Real AI **jobs** (Documenter / Tester / Reviewer) come back as
`CompletedWithErrors` with `inputToken: 0`, `outputToken: 0`, ~1s duration — i.e.
they fail **before** the model is ever called. Root cause is **GCP IAM on the
Wynxx backend**, not the integration: the Wynxx backend service account (project
`wynxx-tests`) lacks `aiplatform.endpoints.predict` on the Gemini model. Fix by
granting that SA `roles/aiplatform.user` (or enabling the model) — then the same
`run_documenter` call returns generated documentation.

The MCP wire, OAuth, `authenticate`, `set_llm`, job submission, `jobId`, and
status polling all work; only the model invocation on Wynxx's side is blocked.

## Files

| File | Purpose |
|---|---|
| `integration_real_native.py` | ADK ↔ native `@wynxx/mcp`: discover all tools, call read-only ones |
| `explore_real.py` | List real catalogs + dump job-tool input schemas |
| `run_real_job.py` | Run a real Code Documenter job end-to-end |
| `agent_llm_real.py` | LLM-driven ADK agent (Vertex Gemini 3) over the native Wynxx MCP |
| `run_workflow_real.py` | Full SequentialAgent/ParallelAgent workflow via an ADK Runner |

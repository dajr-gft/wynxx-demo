# SDLC Orchestration Agent (ADK 2.0)

A graph-based, multi-agent SDLC workflow that consumes the Wynxx MCP server. It
expands the article's ADK 2.0 example and follows the structure and conventions
of [google/adk-samples](https://github.com/google/adk-samples/tree/main/python/agents).

## Overview

Most enterprise SDLC flows are deterministic graphs, not free-form agent loops.
This agent analyzes a repository once, fans the findings out to three parallel
agents — documentation, tests, and modernization — and fans them back in at a
**human-in-the-loop** approval gate before any artifact is published.

It runs **offline by default** (deterministic stub agents, no models or MCP
server required). With `SDLC_MODE=real` it builds the genuine ADK 2.0
orchestration — `SequentialAgent` + `ParallelAgent` from `google.adk.agents`,
with the human-in-the-loop gate as a `before_agent_callback` — calling the Wynxx
MCP server and deployable to Vertex AI Agent Engine.

## Agent Details

| Attribute | Detail |
|---|---|
| Interaction | Workflow (`SequentialAgent` + `ParallelAgent`) |
| Pattern | Fan-out / fan-in with a human-in-the-loop gate |
| Sub-agents | `repo_analyst`, `doc_writer`, `test_strategist`, `modernization_advisor` |
| Tools | Wynxx MCP server (shared `McpToolset`) |
| Models | `gemini-3.1-pro-preview` (reasoning), `gemini-3.5-flash` (volume) — Vertex **global** endpoint |

Three design choices from the article are encoded here:

- **Different models for different roles.** Gemini 3 Pro (`gemini-3.1-pro-preview`)
  for reasoning-heavy agents (analysis, modernization); Gemini 3 Flash
  (`gemini-3.5-flash`) for high-volume agents (docs, tests). Swapping is a
  one-line change in `config.py`. Gemini 3 is served on the Vertex **global**
  endpoint, so set `GOOGLE_CLOUD_LOCATION=global` in real mode.
- **Human-in-the-loop as a first-class step.** In real mode the approval gate is
  a `before_agent_callback` on the publish agent — it short-circuits publication
  until `approved` is set in session state. (The offline runtime models the same
  gate as a node attribute.)
- **Memory (official agentic component).** The analyst uses ADK `preload_memory`
  to recall prior assessments of the same repository — backed by Vertex AI Agent
  Engine **Sessions** (short-term) and **Memory Bank** (long-term) in production.

## Architecture

```
                ┌─────────────┐
                │   analyze   │  (repo_analyst, gemini-3.1-pro-preview)
                └──────┬──────┘
                       │ findings
                ┌──────▼──────┐
                │   fan_out   │
                └──┬───┬───┬──┘
        ┌──────────┘   │   └──────────┐
 ┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼───────┐
 │  document  │ │    test    │ │  modernize   │
 │ doc_writer │ │ strategist │ │   advisor    │
 └──────┬─────┘ └──────┬─────┘ └──────┬───────┘
        └──────────┐   │   ┌──────────┘
              ┌────▼───▼───▼────┐
              │ review_and_publish │  ← human-in-the-loop gate
              └─────────┬──────────┘
                        ▼
                  SDLC package
```

## Project structure

```
adk-agent-workflow/
├── sdlc_workflow/
│   ├── agent.py          # real: SequentialAgent + ParallelAgent + HITL gate;
│   │                     # stub: deterministic agents on graph.py
│   ├── prompt.py         # agent instructions
│   ├── graph.py          # self-contained runtime for the OFFLINE stub path
│   ├── config.py         # SDLC_* settings (mode, models, MCP url)
│   └── __main__.py       # `python -m sdlc_workflow` offline demo
├── deployment/
│   └── deploy.py         # --create / --delete / --list on Agent Engine
├── eval/                 # offline golden eval + ADK AgentEvaluator
├── tests/                # unit tests (stub runtime)
├── run_workflow_real.py  # real: full root_agent workflow via an ADK Runner
├── agent_llm_real.py     # real: one LlmAgent (Gemini 3) over the native Wynxx MCP
├── integration_real.py   # real: ADK <-> repo MCP server (HTTP), no model needed
├── integration_real_native.py  # real: ADK <-> native @wynxx/mcp (stdio)
├── explore_real.py       # real product: list catalogs + job-tool schemas
├── run_real_job.py       # real product: run a Code Documenter job end-to-end
├── SETUP_REAL.md         # setup notes for the real-product tests
├── requirements.txt / requirements-real.txt
├── pyproject.toml
└── .env.example
```

## Setup and Installation

```bash
cd integrations/adk-agent-workflow
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt          # base (offline) + tests
# For real mode + deployment:
# pip install -r requirements-real.txt
cp .env.example .env
```

## Running the Agent

Offline demo (stub agents, no cloud):

```bash
python -m sdlc_workflow
```

Real mode (genuine ADK `SequentialAgent`/`ParallelAgent` + Gemini 3, calling the
Wynxx MCP server). Gemini 3 needs the Vertex **global** endpoint and ADC:

```bash
export SDLC_MODE=real
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=my-project
export GOOGLE_CLOUD_LOCATION=global         # Gemini 3 is served on global
export SDLC_MCP_URL=https://wynxx-mcp-server-xxxxx.run.app/mcp
gcloud auth application-default login        # ADC for Vertex

adk run sdlc_workflow                        # or: adk web
python run_workflow_real.py                  # or drive root_agent via a Runner
```

To exercise the **real Wynxx product** (the native `@wynxx/mcp`, OAuth), see
[`SETUP_REAL.md`](SETUP_REAL.md).

## Running Tests

```bash
pip install ".[dev]"
pytest tests       # unit tests
pytest eval        # golden eval (+ ADK evalset when the runtime is available)
```

## Deployment

Deploy to Vertex AI Agent Engine (sub-second cold starts, OpenTelemetry tracing,
egress through Agent Gateway):

```bash
pip install -r requirements-real.txt "google-cloud-aiplatform[adk,agent_engines]"
python deployment/deploy.py --create
python deployment/deploy.py --list
python deployment/deploy.py --delete --resource_id=<AGENT_ENGINE_ID>
```

Once deployed, the same workflow is discoverable from the **Gemini Enterprise
app**, governed by the same Agent Gateway and audited the same way.

## Customization

- **Swap models** — edit `SDLC_MODEL_PRO` / `SDLC_MODEL_FLASH` in `.env`.
- **Tune behaviour** — edit instructions in `sdlc_workflow/prompt.py`.
- **Add a step** — add an `LlmAgent` (or nest a `ParallelAgent`/`SequentialAgent`)
  in `agent.py` and list it in the `SequentialAgent` (real mode); for the offline
  runtime, add a `@node` and list it in the `Workflow`.
- **Human approval** — real mode gates on session state `approved` via a
  `before_agent_callback`; wire it to your approval system (or a Gemini Enterprise
  action). The offline runtime takes an `approver(node, state) -> bool`.

## Disclaimer

This is a reference example, not a production-ready product. The topology,
governance integration, and deployment shape are the parts intended for reuse.
Real mode uses the genuine ADK 2.0 orchestration (`SequentialAgent` /
`ParallelAgent` from `google.adk.agents`) and is deployable to Agent Engine;
`graph.py` is a small self-contained runtime that runs the same topology offline
(stub agents) for CI and demos. Validated end-to-end against the real Wynxx MCP
with Gemini 3 — see [`SETUP_REAL.md`](SETUP_REAL.md).

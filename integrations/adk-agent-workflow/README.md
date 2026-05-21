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
server required), and against the **real** ADK 2.0 runtime + Wynxx MCP server
when `SDLC_MODE=real`.

## Agent Details

| Attribute | Detail |
|---|---|
| Interaction | Workflow (graph) |
| Pattern | Fan-out / fan-in with a human-in-the-loop gate |
| Sub-agents | `repo_analyst`, `doc_writer`, `test_strategist`, `modernization_advisor` |
| Tools | Wynxx MCP server (shared `McpToolset`) |
| Models | Gemini 3 Pro (reasoning), Gemini 3 Flash (volume) |

Two design choices from the article are encoded here:

- **Different models for different roles.** Gemini 3 Pro for reasoning-heavy
  nodes (analysis, modernization); Gemini 3 Flash for high-volume nodes (docs,
  tests). Swapping is a one-line change in `config.py`.
- **Human-in-the-loop as a graph primitive.** `human_in_the_loop=True` is a node
  attribute, not a wrapper. The approval gate is part of the graph.

## Architecture

```
                ┌─────────────┐
                │   analyze   │  (repo_analyst, Gemini 3 Pro)
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
│   ├── agent.py          # module-level agents + graph nodes + root_agent
│   ├── prompt.py         # agent instructions
│   ├── graph.py          # ADK 2.0 graph primitives (+ local fallback runtime)
│   ├── config.py         # SDLC_* settings
│   └── __main__.py       # `python -m sdlc_workflow` local demo
├── deployment/
│   └── deploy.py         # --create / --delete / --list on Agent Engine
├── eval/
│   ├── data/             # evalset + golden artifacts
│   └── test_eval.py      # offline golden eval + ADK AgentEvaluator
├── tests/
│   └── test_workflow.py
├── requirements.txt      # base (stub/local + tests)
├── requirements-real.txt # google-adk for real mode + deploy
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

Real mode (ADK agents calling the Wynxx MCP server):

```bash
export SDLC_MODE=real
export SDLC_MCP_URL=https://wynxx-mcp-server-xxxxx.run.app/mcp
adk run sdlc_workflow      # or: adk web
```

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
- **Add a node** — add a `@node` in `agent.py` and list it in the `Workflow`.
- **Real human approval** — pass your own `approver(node_name, state) -> bool`
  to `run_workflow`, or wire the gate to your approval system.

## Disclaimer

This is a reference example, not a production-ready product. The stub agents
return illustrative output; the graph topology, governance integration, and
deployment shape are the parts intended for reuse. The ADK 2.0 graph API
(`google.adk.workflows`) reflects the post-Next '26 runtime; `graph.py` ships a
faithful local fallback so the example runs today.

# ADK Agent Archetype

This project is the **target architecture** for modernizing a **legacy business
domain into a Google ADK 2.0 agent**. Use it as the starting point and fill it in
to implement the business rules you are given.

## What this application is

A minimal, runnable Google ADK agent package (`domain_agent/`). Each cohesive
business domain becomes **one** `LlmAgent`: its tools are the domain operations
and its instruction encodes the domain's business rules.

## How to fill it (for the code generator)

Given a domain's business rules, generate:

- **`domain_agent/agent.py`** — `root_agent = LlmAgent(...)`, named after the
  domain, wiring the tools below and the instruction.
- **`domain_agent/tools.py`** — one typed Python function per domain operation
  (capability). Each function: type-hinted parameters (no defaults for values the
  model must supply), a docstring describing the business contract, and a `dict`
  return containing a `status` key.
- **`domain_agent/prompt.py`** — the agent `instruction`: the domain's
  responsibilities plus every business rule, as the single source of truth.

Keep `domain_agent/__init__.py` as `from . import agent` so the ADK CLI
(`adk run` / `adk web`) can import the package.

## Conventions

- **Model:** Gemini on Vertex AI (global endpoint). `gemini-3.5-flash` by default;
  `gemini-3.1-pro-preview` for reasoning-heavy domains.
- **One agent per domain, one tool per operation;** business rules live in the
  instruction, not scattered across tools.
- Tools return a `dict` with a `status` key; cover every business rule provided.

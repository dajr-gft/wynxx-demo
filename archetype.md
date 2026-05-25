# ADK Agent Archetype

This project is the **target architecture** for modernizing a **legacy business
domain into a Google ADK 2.0 agent**. The code generator clones this repo and
fills the `domain_agent/` package with the domain it is given, following the
patterns in **Architecture Layers** below.

## What this application is

A minimal, runnable Google ADK agent package. Each cohesive business domain
becomes one `LlmAgent`: its tools are the domain operations and its instruction
encodes the domain's business rules.

## Architecture Layers

### Agent
File: `domain_agent/agent.py`. Defines the module-level `root_agent` — an
`LlmAgent` named `<domain>_domain_agent` — wiring the tools and the instruction.
One agent per domain.

```python
from google.adk.agents import LlmAgent
from .prompt import DOMAIN_INSTRUCTION
from .tools import operation_a, operation_b

MODEL = "gemini-3.5-flash"  # use "gemini-3.1-pro-preview" for reasoning-heavy domains

root_agent = LlmAgent(
    name="<domain>_domain_agent",
    model=MODEL,
    description="Modernized '<Domain>' business domain (from a legacy Java service).",
    instruction=DOMAIN_INSTRUCTION,
    tools=[operation_a, operation_b],
)
```

### Tools
File: `domain_agent/tools.py`. One typed function per domain operation (one per
business-rule category). Type-hint every parameter; write a docstring with Args
and Returns; return a `dict` containing a `status` key. Enforce the relevant
business rules inside each function.

```python
from typing import Any

def operation_a(param: str) -> dict[str, Any]:
    """Do <operation>, enforcing rules BR-xxx.

    Args:
        param: <meaning>.
    Returns:
        dict: ``status`` ("success" | "error") plus the result or error_message.
    """
    return {"status": "success", "result": {}}
```

### Prompt
File: `domain_agent/prompt.py`. A `DOMAIN_INSTRUCTION` string: the domain's
responsibilities plus every business rule, as the single source of truth.

```python
DOMAIN_INSTRUCTION = """\
You are the **<Domain>** domain agent, modernized from a legacy Java service.

Responsibilities:
- Own every business operation of the <Domain> domain.
- Enforce these business rules: <list each rule explicitly>.

For each request: identify the capability, validate inputs against the rules,
execute, and return a structured result. Never act outside the documented
capabilities.
"""
```

## Conventions
- One agent per domain; one tool per operation; business rules in the instruction.
- Keep `domain_agent/__init__.py` as `from . import agent` (so `adk run/web` imports it).
- Model: Gemini on Vertex AI (global endpoint).

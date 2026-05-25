# Beachshirts — ADK 2.0 multi-agent system

The legacy **beachshirts** Java microservices app, modernized into a **Google ADK
2.0 multi-agent system**: one coordinator agent that delegates to a sub-agent per
business domain.

## Structure

```
beachshirts_agent/
├── agent.py            # root_agent — the coordinator (LlmAgent with sub_agents)
├── prompt.py           # coordinator routing instruction
└── sub_agents/
    ├── shopping.py     # shopping_agent — Orders domain
    ├── styling.py      # styling_agent  — Design domain
    └── delivery.py     # delivery_agent — Fulfillment domain
```

## Mapping (legacy → ADK)

| Legacy service | ADK sub-agent    | Operations (function tools)                         |
| -------------- | ---------------- | --------------------------------------------------- |
| shopping       | `shopping_agent` | create_order, get_order, cancel_order               |
| styling        | `styling_agent`  | create_design, apply_template, validate_design      |
| delivery       | `delivery_agent` | schedule_delivery, track_delivery, confirm_delivery |

Each domain's business rules live in its sub-agent's `instruction`; each public
operation is a typed function tool. The coordinator routes by domain and can
sequence them (order → design → delivery). Add the remaining beachshirts services
(printing, packaging) as further sub-agents following the same pattern.

## Run

```
adk web                  # dev UI, from this directory
adk run beachshirts_agent
```

Model: Gemini on Vertex AI (global endpoint). `gemini-3.5-flash` by default;
`gemini-3.1-pro-preview` for reasoning-heavy domains.

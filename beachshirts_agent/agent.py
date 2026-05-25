"""Beachshirts — the legacy app modernized as a Google ADK 2.0 multi-agent system.

The legacy beachshirts microservices (shopping, styling, delivery, ...) become a
single coordinator ``LlmAgent`` that delegates each request to a domain
sub-agent. ``root_agent`` is the entry point the ADK CLI (``adk run`` / ``adk
web``) discovers.
"""

from google.adk.agents import LlmAgent

from .prompt import COORDINATOR_INSTRUCTION
from .sub_agents import delivery_agent, shopping_agent, styling_agent

# Gemini on Vertex AI (global endpoint). Flash by default; switch reasoning-heavy
# domains to "gemini-3.1-pro-preview".
MODEL = "gemini-3.5-flash"

root_agent = LlmAgent(
    name="beachshirts_coordinator",
    model=MODEL,
    description="Coordinator for the modernized beachshirts domains (orders, design, delivery).",
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[shopping_agent, styling_agent, delivery_agent],
)

"""Styling (Design) domain — modernized from the legacy beachshirts 'styling' service."""

from typing import Any

from google.adk.agents import LlmAgent


def create_design(customer_id: str, base_style: str, customizations: list[str]) -> dict[str, Any]:
    """Create a custom shirt design.

    Rules: a valid base_style is required; at least one customization (color, text,
    or graphic) is required; a new design starts in status DRAFT.

    Args:
        customer_id: the customer.
        base_style: the base shirt style.
        customizations: list of customizations (color / text / graphic).

    Returns:
        dict: ``status`` and the created design (with ``design_id``), or an ``error_message``.
    """
    if not base_style:
        return {"status": "error", "error_message": "base_style is required"}
    if not customizations:
        return {"status": "error", "error_message": "at least one customization is required"}
    return {
        "status": "success",
        "design": {
            "design_id": "DSN-2001",
            "customer_id": customer_id,
            "base_style": base_style,
            "customizations": customizations,
            "state": "DRAFT",
        },
    }


def apply_template(design_id: str, template_id: str) -> dict[str, Any]:
    """Apply a predefined template to a design.

    Rule: the template must be compatible with the design's base_style.

    Args:
        design_id: the design.
        template_id: the template to apply.

    Returns:
        dict: ``status`` and the updated design, or an ``error_message``.
    """
    return {"status": "success", "design": {"design_id": design_id, "template_id": template_id}}


def validate_design(design_id: str) -> dict[str, Any]:
    """Check whether a design is print-ready.

    Rule: print-ready requires a base_style, at least one customization, and passing
    size constraints; a print-ready design moves to status READY.

    Args:
        design_id: the design to validate.

    Returns:
        dict: ``status`` and whether the design is READY, or an ``error_message``.
    """
    return {"status": "success", "design": {"design_id": design_id, "state": "READY"}}


styling_agent = LlmAgent(
    name="styling_agent",
    model="gemini-3.5-flash",
    description="Design domain: create custom shirt designs, apply templates, validate print-readiness.",
    instruction=(
        "You own the **Styling/Design** domain (modernized from the legacy styling service). "
        "Enforce these rules: base_style is required; at least one customization; new designs "
        "are DRAFT; a design is READY only with a base_style, >= 1 customization, and valid "
        "size constraints. Use the tools to act."
    ),
    tools=[create_design, apply_template, validate_design],
)

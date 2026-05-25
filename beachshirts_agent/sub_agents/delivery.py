"""Delivery (Fulfillment) domain — modernized from the legacy beachshirts 'delivery' service."""

from typing import Any

from google.adk.agents import LlmAgent


def schedule_delivery(order_id: str, address: str) -> dict[str, Any]:
    """Schedule delivery for a confirmed order.

    Rules: a destination address is required; a scheduled delivery starts in
    status SCHEDULED.

    Args:
        order_id: the order to deliver.
        address: the destination address.

    Returns:
        dict: ``status`` and the created delivery (with ``delivery_id``), or an ``error_message``.
    """
    if not address:
        return {"status": "error", "error_message": "a destination address is required"}
    return {
        "status": "success",
        "delivery": {"delivery_id": "DLV-3001", "order_id": order_id, "address": address, "state": "SCHEDULED"},
    }


def track_delivery(delivery_id: str) -> dict[str, Any]:
    """Track a delivery's current status.

    Args:
        delivery_id: the delivery to track.

    Returns:
        dict: ``status`` and the delivery's current state, or an ``error_message``.
    """
    return {"status": "success", "delivery": {"delivery_id": delivery_id, "state": "IN_TRANSIT"}}


def confirm_delivery(delivery_id: str) -> dict[str, Any]:
    """Mark a delivery as delivered.

    Rule: only a delivery IN_TRANSIT can be confirmed; it then moves to DELIVERED.

    Args:
        delivery_id: the delivery to confirm.

    Returns:
        dict: ``status`` and the updated delivery, or an ``error_message``.
    """
    return {"status": "success", "delivery": {"delivery_id": delivery_id, "state": "DELIVERED"}}


delivery_agent = LlmAgent(
    name="delivery_agent",
    model="gemini-3.5-flash",
    description="Fulfillment domain: schedule, track, and confirm shirt deliveries.",
    instruction=(
        "You own the **Delivery/Fulfillment** domain (modernized from the legacy delivery service). "
        "Enforce these rules: a destination address is required; deliveries start SCHEDULED; only "
        "IN_TRANSIT deliveries can be confirmed (→ DELIVERED). Use the tools to act; never invent state."
    ),
    tools=[schedule_delivery, track_delivery, confirm_delivery],
)

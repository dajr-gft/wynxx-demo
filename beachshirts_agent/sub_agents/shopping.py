"""Shopping (Orders) domain — modernized from the legacy beachshirts 'shopping' service."""

from typing import Any

from google.adk.agents import LlmAgent


def create_order(customer_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a new order for a customer.

    Rules: an order must contain at least one item; each item needs a valid shirt
    style and a quantity >= 1; a new order starts in status PENDING.

    Args:
        customer_id: the customer placing the order.
        items: list of ``{"style": str, "quantity": int}`` entries.

    Returns:
        dict: ``status`` and the created order (with ``order_id``), or an ``error_message``.
    """
    if not items:
        return {"status": "error", "error_message": "an order needs at least one item"}
    if any(item.get("quantity", 0) < 1 for item in items):
        return {"status": "error", "error_message": "item quantity must be >= 1"}
    return {
        "status": "success",
        "order": {"order_id": "ORD-1001", "customer_id": customer_id, "items": items, "state": "PENDING"},
    }


def get_order(order_id: str) -> dict[str, Any]:
    """Retrieve an order by id.

    Args:
        order_id: the order identifier.

    Returns:
        dict: ``status`` and the order, or an ``error_message`` if not found.
    """
    return {"status": "success", "order": {"order_id": order_id, "state": "PENDING"}}


def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel an order.

    Rule: only orders in PENDING or CONFIRMED can be cancelled; a cancelled order
    moves to CANCELLED and cannot be modified afterwards.

    Args:
        order_id: the order to cancel.

    Returns:
        dict: ``status`` and the updated order, or an ``error_message``.
    """
    return {"status": "success", "order": {"order_id": order_id, "state": "CANCELLED"}}


shopping_agent = LlmAgent(
    name="shopping_agent",
    model="gemini-3.5-flash",
    description="Orders domain: create, look up, and cancel customer orders for beach shirts.",
    instruction=(
        "You own the **Orders** domain (modernized from the legacy shopping service). "
        "Enforce these rules: an order has at least one item; item quantity >= 1; new "
        "orders are PENDING; only PENDING or CONFIRMED orders can be cancelled. Use the "
        "tools to act; never invent order state."
    ),
    tools=[create_order, get_order, cancel_order],
)

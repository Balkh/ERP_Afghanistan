"""Returns event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.returns")


def on_return_order_created(payload: dict) -> None:
    logger.info("Return order created: %s", payload.get("id"))


def on_return_order_approved(payload: dict) -> None:
    logger.info("Return order approved: %s", payload.get("id"))


def register() -> None:
    EnterpriseEventBus.subscribe("returns.order.created", on_return_order_created)
    EnterpriseEventBus.subscribe("returns.order.approved", on_return_order_approved)

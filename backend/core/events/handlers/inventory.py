"""Inventory event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.inventory")


def on_stock_movement_created(payload: dict) -> None:
    logger.info("Stock movement: %s qty=%s", payload.get("id"), payload.get("quantity"))


def on_batch_expiry_approaching(payload: dict) -> None:
    logger.info("Batch expiring soon: %s", payload.get("batch_number"))


def register() -> None:
    EnterpriseEventBus.subscribe("inventory.stock.moved", on_stock_movement_created)
    EnterpriseEventBus.subscribe("inventory.batch.expiring", on_batch_expiry_approaching)

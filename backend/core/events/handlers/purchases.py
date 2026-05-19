"""Purchase & payment event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.purchases")


def on_purchase_invoice_created(payload: dict) -> None:
    logger.info("Purchase invoice created: %s", payload.get("id"))


def on_purchase_invoice_received(payload: dict) -> None:
    logger.info("Purchase invoice received: %s", payload.get("id"))


def on_supplier_payment_made(payload: dict) -> None:
    logger.info("Supplier payment made: %s", payload.get("id"))


def register() -> None:
    EnterpriseEventBus.subscribe("purchase.invoice.created", on_purchase_invoice_created)
    EnterpriseEventBus.subscribe("purchase.invoice.received", on_purchase_invoice_received)
    EnterpriseEventBus.subscribe("supplier.payment.made", on_supplier_payment_made)

"""Sales & payment event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.sales")


def on_sales_invoice_created(payload: dict) -> None:
    logger.info("Sales invoice created: %s", payload.get("id"))


def on_sales_invoice_dispatched(payload: dict) -> None:
    logger.info("Sales invoice dispatched: %s", payload.get("id"))


def on_customer_payment_received(payload: dict) -> None:
    logger.info("Customer payment received: %s", payload.get("id"))


def register() -> None:
    EnterpriseEventBus.subscribe("sales.invoice.created", on_sales_invoice_created)
    EnterpriseEventBus.subscribe("sales.invoice.dispatched", on_sales_invoice_dispatched)
    EnterpriseEventBus.subscribe("customer.payment.received", on_customer_payment_received)

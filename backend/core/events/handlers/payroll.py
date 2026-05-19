"""Payroll event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.payroll")


def on_payroll_cycle_closed(payload: dict) -> None:
    logger.info("Payroll cycle closed: %s", payload.get("id"))


def register() -> None:
    EnterpriseEventBus.subscribe("payroll.cycle.closed", on_payroll_cycle_closed)

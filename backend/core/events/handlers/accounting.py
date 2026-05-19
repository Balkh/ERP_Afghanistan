"""Accounting event handlers. Log-only, no side effects."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.accounting")


def on_journal_entry_posted(payload: dict) -> None:
    logger.info("Journal entry posted: %s", payload.get("id"))


def on_journal_entry_reversed(payload: dict) -> None:
    logger.info("Journal entry reversed: %s", payload.get("id"))


def register() -> None:
    EnterpriseEventBus.subscribe("accounting.journal.posted", on_journal_entry_posted)
    EnterpriseEventBus.subscribe("accounting.journal.reversed", on_journal_entry_reversed)

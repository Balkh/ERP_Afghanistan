"""Domain event handler modules. Isolated, stateless, no cross-module imports."""
import logging

from core.events import EnterpriseEventBus

logger = logging.getLogger("erp.events.handlers")


def register_all_handlers() -> None:
    """Register all domain event handlers. Called once on startup."""
    from core.events.handlers.sales import register as reg_sales
    from core.events.handlers.purchases import register as reg_purchases
    from core.events.handlers.inventory import register as reg_inventory
    from core.events.handlers.accounting import register as reg_accounting
    from core.events.handlers.returns import register as reg_returns
    from core.events.handlers.payroll import register as reg_payroll
    reg_sales()
    reg_purchases()
    reg_inventory()
    reg_accounting()
    reg_returns()
    reg_payroll()
    logger.info("All event handlers registered (%d event types)", len(EnterpriseEventBus._subscribers))

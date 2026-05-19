"""
Backward-compatible re-export.
StockIntegrationService.process_transfer now lives on the canonical class
in stock_integration.py to avoid a duplicate class definition.
"""
from inventory.service.stock_integration import StockIntegrationService

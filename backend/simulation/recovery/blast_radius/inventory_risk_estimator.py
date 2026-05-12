"""Inventory risk estimation — estimates inventory impact from detected corruption."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import InventoryRiskEstimate, IntegritySeverity


class InventoryRiskEstimator:
    def __init__(self, max_history: int = 100):
        self._estimates: deque = deque(maxlen=max_history)

    def estimate_inventory_risk(self, items_mismatched: int,
                                affected_warehouses: Optional[List[str]] = None,
                                estimated_value_at_risk: float = 0.0,
                                total_batch_count: int = 0) -> Dict[str, Any]:
        affected_warehouses = affected_warehouses or []
        potential_corrections = items_mismatched + total_batch_count
        if items_mismatched > 50 or estimated_value_at_risk > 50000:
            risk = IntegritySeverity.CRITICAL
        elif items_mismatched > 20 or estimated_value_at_risk > 10000:
            risk = IntegritySeverity.HIGH
        elif items_mismatched > 5 or estimated_value_at_risk > 1000:
            risk = IntegritySeverity.MEDIUM
        elif items_mismatched > 0:
            risk = IntegritySeverity.LOW
        else:
            risk = IntegritySeverity.INFO
        estimate = InventoryRiskEstimate(
            estimated_items_affected=items_mismatched,
            risk_level=risk, affected_warehouses=affected_warehouses,
            potential_batch_corrections=potential_corrections,
            estimated_value_at_risk=estimated_value_at_risk,
        )
        self._estimates.append({
            'items_affected': items_mismatched,
            'risk_level': risk.value,
            'value_at_risk': estimated_value_at_risk,
        })
        return {
            'estimated_items_affected': items_mismatched,
            'risk_level': risk.value,
            'affected_warehouses': affected_warehouses,
            'potential_batch_corrections': potential_corrections,
            'estimated_value_at_risk': estimated_value_at_risk,
        }

    def clear(self):
        self._estimates.clear()

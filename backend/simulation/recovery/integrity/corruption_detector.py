"""Corruption detection — detects data corruption in workflows and financial data."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import CorruptionRecord, IntegritySeverity, CorruptionType


class CorruptionDetector:
    def __init__(self, max_history: int = 200):
        self._corruption_records: deque = deque(maxlen=max_history)
        self._detection_count: int = 0

    def detect_financial_corruption(self, journal_balance: float, expected_balance: float,
                                    tick: int, source_module: str = 'accounting') -> Optional[Dict[str, Any]]:
        if abs(journal_balance - expected_balance) < 0.001:
            return None
        self._detection_count += 1
        gap = abs(journal_balance - expected_balance)
        severity = (IntegritySeverity.CRITICAL if gap > 1000
                    else IntegritySeverity.HIGH if gap > 100
                    else IntegritySeverity.MEDIUM)
        return self._create_record(
            CorruptionType.FINANCIAL, severity, source_module,
            f"Journal imbalance: {gap}", tick,
            estimated_blast_radius=min(100.0, gap / 10),
        )

    def detect_inventory_corruption(self, expected_qty: float, actual_qty: float,
                                    tick: int, source_module: str = 'inventory') -> Optional[Dict[str, Any]]:
        if abs(expected_qty - actual_qty) < 0.001:
            return None
        self._detection_count += 1
        diff = abs(expected_qty - actual_qty)
        severity = (IntegritySeverity.CRITICAL if diff > 100
                    else IntegritySeverity.HIGH if diff > 10
                    else IntegritySeverity.MEDIUM)
        return self._create_record(
            CorruptionType.INVENTORY, severity, source_module,
            f"Inventory qty mismatch: {diff}", tick,
        )

    def detect_orphan_state(self, orphan_count: int, tick: int,
                            source_module: str = 'workflow') -> Optional[Dict[str, Any]]:
        if orphan_count == 0:
            return None
        self._detection_count += 1
        severity = (IntegritySeverity.CRITICAL if orphan_count > 10
                    else IntegritySeverity.HIGH if orphan_count > 3
                    else IntegritySeverity.MEDIUM)
        return self._create_record(
            CorruptionType.ORPHAN_STATE, severity, source_module,
            f"{orphan_count} orphan state(s) detected", tick,
        )

    def _create_record(self, ctype: CorruptionType, severity: IntegritySeverity,
                       source: str, description: str, tick: int,
                       estimated_blast_radius: float = 0.0) -> Dict[str, Any]:
        corruption_id = f"corr_{self._detection_count}"
        record = CorruptionRecord(
            corruption_id=corruption_id, corruption_type=ctype,
            severity=severity, source_module=source,
            description=description, detected_at_tick=tick,
            estimated_blast_radius=estimated_blast_radius,
            requires_manual_intervention=severity in (IntegritySeverity.HIGH, IntegritySeverity.CRITICAL),
        )
        self._corruption_records.append(record)
        return {
            'corruption_id': corruption_id, 'type': ctype.value,
            'severity': severity.value, 'description': description,
            'blast_radius': estimated_blast_radius,
            'requires_manual': record.requires_manual_intervention,
        }

    def get_detection_count(self) -> int:
        return self._detection_count

    def clear(self):
        self._corruption_records.clear()
        self._detection_count = 0

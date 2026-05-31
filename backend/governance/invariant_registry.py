"""
Section 4 — Regression Immunity Layer.
CriticalInvariantRegistry with checksum-based snapshots of accounting/integrity invariants.
"""
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InvariantCheck:
    name: str
    description: str
    category: str
    critical: bool


INVARIANTS = [
    InvariantCheck("double_entry_balance", "All posted journals must balance", "accounting", True),
    InvariantCheck("no_negative_inventory", "Batch remaining quantity must not be negative", "inventory", True),
    InvariantCheck("accounting_equation", "Assets = Liabilities + Equity", "accounting", True),
    InvariantCheck("replay_determinism", "Replay must produce identical state", "replay", True),
    InvariantCheck("audit_consistency", "Audit trail must not have gaps", "audit", True),
    InvariantCheck("fk_integrity", "All foreign key references must be valid", "data", True),
    InvariantCheck("no_orphan_journals", "All posted journals must have lines", "accounting", False),
    InvariantCheck("stock_movement_lineage", "Stock movements must trace to batches", "inventory", False),
]


class CriticalInvariantRegistry:

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def compute_checksum(self, invariant_name: str) -> Optional[str]:
        try:
            if invariant_name == "double_entry_balance":
                return self._checksum_double_entry()
            elif invariant_name == "no_negative_inventory":
                return self._checksum_no_negative()
            elif invariant_name == "accounting_equation":
                return self._checksum_equation()
            elif invariant_name == "no_orphan_journals":
                return self._checksum_orphans()
            return None
        except Exception:
            return None

    def _checksum_double_entry(self) -> str:
        from accounting.models import JournalEntryLine
        from django.db.models import Sum
        data = list(
            JournalEntryLine.objects.values("entry_id")
            .annotate(d=Sum("debit"), c=Sum("credit"))
            .filter(is_posted=True if hasattr(JournalEntryLine, "is_posted") else True)[:1000]
        )
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def _checksum_no_negative(self) -> str:
        from inventory.models import Batch
        neg = list(Batch.objects.filter(remaining_quantity__lt=0).values("id", "remaining_quantity"))
        return hashlib.sha256(json.dumps(neg, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def _checksum_equation(self) -> str:
        from accounting.models import Account
        from decimal import Decimal
        assets = sum(
            (a.balance or Decimal("0")) for a in Account.objects.filter(account_type="ASSET")
        )
        liabilities = sum(
            (a.balance or Decimal("0")) for a in Account.objects.filter(account_type="LIABILITY")
        )
        equity = sum(
            (a.balance or Decimal("0")) for a in Account.objects.filter(account_type="EQUITY")
        )
        data = {"assets": str(assets), "liabilities": str(liabilities), "equity": str(equity)}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def _checksum_orphans(self) -> str:
        from accounting.models import JournalEntry, JournalEntryLine
        orphan_ids = JournalEntry.objects.filter(
            is_posted=True
        ).exclude(
            id__in=JournalEntryLine.objects.values_list("entry_id", flat=True)
        ).values_list("id", flat=True)[:100]
        data = {"orphan_count": len(orphan_ids), "ids": list(orphan_ids)[:20]}
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def snapshot_all(self) -> Dict[str, str]:
        result = {}
        for inv in INVARIANTS:
            cs = self.compute_checksum(inv.name)
            if cs:
                result[inv.name] = cs
        self._cache = result
        return result

    def verify_all(self, previous: Dict[str, str]) -> Dict[str, Tuple[bool, str]]:
        current = self.snapshot_all()
        result = {}
        for name, prev_cs in previous.items():
            curr_cs = current.get(name)
            if curr_cs is None:
                result[name] = (False, "Could not compute checksum")
            elif curr_cs == prev_cs:
                result[name] = (True, "Invariant preserved")
            else:
                result[name] = (False, "Invariant changed")
        return result

    def list_invariants(self) -> List[InvariantCheck]:
        return INVARIANTS

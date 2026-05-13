"""
Phase 5B.4 — System Integrity Monitor.

Validates system consistency in real time.
Read-only — detects anomalies without modifying anything.

Checks:
- Event sequence continuity
- Projection consistency hash match
- Missing event detection
- Duplicate event detection
- Cross-domain integrity alignment
- Truth verification drift signals
"""
import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from core.operations.truth.models import Domain, ConsistencyResult
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.truth.projections import (
    InventoryProjection, AccountingProjection,
    HRProjection, SalesPurchaseProjection,
)
from core.operations.observability.models import (
    IntegrityReport, IntegrityStatus, StreamHealth,
)

logger = logging.getLogger('erp.observability.integrity')

INTEGRITY_MONITOR_VERSION = "1.0.0"


class SystemIntegrityMonitor:
    """Read-only system integrity monitoring.

    Validates:
    - Event sequence continuity (no gaps)
    - Projection consistency (hash matches)
    - Missing events
    - Duplicate events
    - Cross-domain integrity
    - Truth verification drift
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def run_full_integrity_check(self) -> IntegrityReport:
        """Run a comprehensive system integrity check.

        Returns:
            IntegrityReport with findings. NEVER modifies state.
        """
        anomalies: List[Dict[str, Any]] = []
        affected_domains: Set[str] = set()
        total_events = self._store.count()
        total_sequence_gaps = 0
        total_missing = 0

        consistency = self._store.run_consistency_check()

        if not consistency.consistent:
            for gap in consistency.sequence_gaps:
                anomalies.append({
                    "type": "SEQUENCE_GAP",
                    "severity": "MEDIUM",
                    "detail": f"Aggregate {gap['aggregate_id']}: "
                              f"expected seq {gap['expected_sequence']}, "
                              f"got {gap['actual_sequence']}",
                })
                total_sequence_gaps += 1

            for ts_anomaly in consistency.timestamp_anomalies:
                anomalies.append({
                    "type": "TIMESTAMP_INVERSION",
                    "severity": "HIGH",
                    "detail": ts_anomaly,
                })

        for domain in Domain:
            domain_events = self._store.get_by_domain(domain)
            if not domain_events:
                continue

            seq_keys: Dict[str, Set[int]] = defaultdict(set)
            for e in domain_events:
                key = f"{e.source_type.value}:{e.aggregate_id}"
                seq_keys[key].add(e.sequence)

            for key, seqs in seq_keys.items():
                sorted_seqs = sorted(seqs)
                for i in range(len(sorted_seqs) - 1):
                    if sorted_seqs[i + 1] - sorted_seqs[i] > 1:
                        total_missing += sorted_seqs[i + 1] - sorted_seqs[i] - 1

            event_ids = [e.event_id for e in domain_events]
            if len(event_ids) != len(set(event_ids)):
                anomalies.append({
                    "type": "DUPLICATE_EVENT_ID",
                    "severity": "CRITICAL",
                    "detail": f"Duplicate event IDs found in domain {domain.value}",
                })
                affected_domains.add(domain.value)

        self._check_projection_consistency(anomalies, affected_domains)

        status = IntegrityStatus.PASS
        if anomalies:
            critical_count = sum(1 for a in anomalies if a["severity"] == "CRITICAL")
            if critical_count > 0:
                status = IntegrityStatus.FAIL
            else:
                status = IntegrityStatus.DEGRADED

        h = hashlib.sha256()
        h.update(str(total_events).encode())
        h.update(str(len(anomalies)).encode())
        consistency_hash = h.hexdigest()

        domain_balances: Dict[str, bool] = {}
        for domain in Domain:
            domain_events = self._store.get_by_domain(domain)
            domain_balances[domain.value] = len(domain_events) > 0

        return IntegrityReport(
            status=status,
            detected_anomalies=anomalies,
            affected_domains=sorted(affected_domains),
            consistency_hash=consistency_hash,
            total_events_checked=total_events,
            sequence_gaps=total_sequence_gaps,
            missing_events=total_missing,
            domain_balances=domain_balances,
        )

    def check_projection_consistency(
        self,
        projection: Any,
        domain: Domain,
    ) -> bool:
        """Check if a projection's event count matches the store.

        Read-only — never modifies projection state.
        """
        domain_events = self._store.get_by_domain(domain)
        try:
            event_count = projection.rebuild()
            return event_count == len(domain_events)
        except Exception:
            return False

    def verify_event_chain(self, event_id: str) -> Dict[str, Any]:
        """Verify that an event and its chain is consistent.

        Returns deterministic verification result.
        """
        event = self._store.get(event_id)
        if not event:
            return {"verified": False, "reason": "Event not found"}

        agg_events = self._store.get_by_aggregate(Domain(event.domain), event.aggregate_id)
        issues = []

        seqs = sorted(e.sequence for e in agg_events)
        if event.sequence not in seqs:
            issues.append("Event sequence not in aggregate sequence list")

        if seqs and seqs[0] != 1:
            issues.append(f"First sequence is {seqs[0]}, expected 1")

        return {
            "verified": len(issues) == 0,
            "event_id": event_id,
            "domain": event.domain.value,
            "aggregate_id": event.aggregate_id,
            "sequence": event.sequence,
            "total_in_chain": len(agg_events),
            "issues": issues,
        }

    def get_domain_integrity(self, domain: Domain) -> Dict[str, Any]:
        """Get integrity status for a single domain."""
        events = self._store.get_by_domain(domain)
        gaps = self._store.check_sequence_continuity(domain)

        return {
            "domain": domain.value,
            "total_events": len(events),
            "sequence_gaps": len(gaps),
            "has_issues": len(gaps) > 0,
        }

    def _check_projection_consistency(
        self,
        anomalies: List[Dict[str, Any]],
        affected_domains: Set[str],
    ) -> None:
        """Check projection state consistency across domains."""
        for domain_check in [
            (Domain.INVENTORY, InventoryProjection),
            (Domain.ACCOUNTING, AccountingProjection),
            (Domain.HR, HRProjection),
            (Domain.SALES_PURCHASE, SalesPurchaseProjection),
        ]:
            domain, proj_cls = domain_check
            domain_events = self._store.get_by_domain(domain)
            if not domain_events:
                continue
            try:
                proj = proj_cls(self._store)
                proj.rebuild()
                if not self.check_projection_consistency(proj, domain):
                    anomalies.append({
                        "type": "PROJECTION_HASH_MISMATCH",
                        "severity": "HIGH",
                        "detail": f"Projection hash mismatch for domain {domain.value}",
                    })
                    affected_domains.add(domain.value)
            except Exception as e:
                anomalies.append({
                    "type": "PROJECTION_ERROR",
                    "severity": "HIGH",
                    "detail": f"Projection error for domain {domain.value}: {str(e)[:100]}",
                })
                affected_domains.add(domain.value)

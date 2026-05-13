"""
Phase 5B.8 — Anomaly Foresight Engine.

Predicts future anomalies BEFORE they occur using:
- Drift patterns
- Event frequency deviation
- Financial inconsistency trends

Read-only. Deterministic. No side effects.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from typing import Any, Dict, List, Optional, Set

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    AnomalyWarning, InsightSeverity, ForecastDirection,
)

logger = logging.getLogger('erp.autonomous.foresight')

ANOMALY_FORESIGHT_VERSION = "1.0.0"
WINDOW_DAYS = 7


class AnomalyForesightEngine:
    """Predicts future anomalies using deterministic pattern analysis.

    All predictions are extrapolations from Event Store patterns.
    No ML, no black-box, no hallucination.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def predict_inventory_anomalies(self) -> List[AnomalyWarning]:
        """Predict future inventory anomalies."""
        warnings: List[AnomalyWarning] = []
        events = self._store.get_by_domain(Domain.INVENTORY)
        if len(events) < 5:
            return warnings

        daily_counts = self._get_daily_counts(events)
        values = list(daily_counts.values())
        if len(values) < 3:
            return warnings

        avg = sum(values) / len(values)
        std = sqrt(sum((v - avg) ** 2 for v in values) / len(values)) if len(values) > 1 else 0

        out_moves = [e for e in events if e.event_type == "stock_movement"
                     and e.payload.get("direction") == "out"]
        in_moves = [e for e in events if e.event_type == "stock_movement"
                    and e.payload.get("direction") == "in"]

        if len(in_moves) > 0 and len(out_moves) > len(in_moves) * 3:
            imbalance = len(out_moves) / max(len(in_moves), 1)
            warnings.append(AnomalyWarning(
                domain="inventory",
                signal_type="rapid_depletion",
                severity=InsightSeverity.CRITICAL if imbalance > 5 else InsightSeverity.WARNING,
                description=f"Outbound ({len(out_moves)}) exceeds inbound ({len(in_moves)}) "
                            f"by {imbalance:.1f}x. Stockout risk in {WINDOW_DAYS} days.",
                current_value=float(len(out_moves)),
                threshold_value=float(len(in_moves)),
                deviation_pct=(imbalance - 1) * 100,
                supporting_event_ids=[e.event_id for e in (out_moves + in_moves)[:5]],
                estimated_occurrence=(datetime.utcnow() + timedelta(days=WINDOW_DAYS)).isoformat() + "Z",
                confidence_score=min(0.9, 0.5 + (imbalance / 10)),
            ))

        recent_out = len([e for e in out_moves if self._is_recent(e.timestamp, 7)])
        if recent_out > avg * 2 and std > 0:
            z_score = (recent_out - avg) / max(std, 0.1)
            warnings.append(AnomalyWarning(
                domain="inventory",
                signal_type="activity_burst",
                severity=InsightSeverity.WARNING,
                description=f"Unusual activity burst: {recent_out} events in 7 days "
                            f"(z-score: {z_score:.1f}).",
                current_value=float(recent_out),
                threshold_value=float(avg),
                deviation_pct=(recent_out / max(avg, 1) - 1) * 100,
                estimated_occurrence=datetime.utcnow().isoformat() + "Z",
                confidence_score=min(0.85, abs(z_score) / 5),
            ))

        return warnings

    def predict_financial_anomalies(self) -> List[AnomalyWarning]:
        """Predict future financial anomalies."""
        warnings: List[AnomalyWarning] = []
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        if len(events) < 3:
            return warnings

        reversals = [e for e in events if e.event_type == "journal_entry_reversed"]
        if len(reversals) >= 2:
            recent_reversals = [e for e in reversals if self._is_recent(e.timestamp, 14)]
            if len(recent_reversals) >= 2:
                warnings.append(AnomalyWarning(
                    domain="accounting",
                    signal_type="reversal_cluster",
                    severity=InsightSeverity.CRITICAL,
                    description=f"{len(recent_reversals)} reversals in 14 days. "
                                "Potential accounting process issue.",
                    current_value=float(len(recent_reversals)),
                    threshold_value=1.0,
                    deviation_pct=(len(recent_reversals) - 1) * 100,
                    supporting_event_ids=[e.event_id for e in recent_reversals],
                    estimated_occurrence=datetime.utcnow().isoformat() + "Z",
                    confidence_score=0.75,
                ))

        return warnings

    def predict_hr_anomalies(self) -> List[AnomalyWarning]:
        """Predict future HR anomalies."""
        warnings: List[AnomalyWarning] = []
        events = self._store.get_by_domain(Domain.HR)
        if len(events) < 3:
            return warnings

        terminations = [e for e in events if e.event_type == "employee_terminated"]
        if len(terminations) >= 2:
            recent_terms = [e for e in terminations if self._is_recent(e.timestamp, 30)]
            if len(recent_terms) >= 2:
                warnings.append(AnomalyWarning(
                    domain="hr",
                    signal_type="attrition_risk",
                    severity=InsightSeverity.WARNING,
                    description=f"{len(recent_terms)} terminations in 30 days. "
                                "Elevated attrition risk.",
                    current_value=float(len(recent_terms)),
                    threshold_value=1.0,
                    deviation_pct=(len(recent_terms) - 1) * 100,
                    supporting_event_ids=[e.event_id for e in recent_terms],
                    estimated_occurrence=datetime.utcnow().isoformat() + "Z",
                    confidence_score=0.7,
                ))

        return warnings

    def predict_all(self) -> List[AnomalyWarning]:
        """Run all anomaly predictions."""
        warnings: List[AnomalyWarning] = []
        warnings.extend(self.predict_inventory_anomalies())
        warnings.extend(self.predict_financial_anomalies())
        warnings.extend(self.predict_hr_anomalies())
        return warnings

    def _get_daily_counts(self, events: List[Any]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in events:
            day = e.timestamp[:10] if len(e.timestamp) >= 10 else "unknown"
            counts[day] += 1
        return counts

    def _is_recent(self, timestamp: str, days: int) -> bool:
        try:
            ts = timestamp.replace("Z", "+00:00")
            if "+" in ts and ts.endswith("00:00"):
                dt = datetime.fromisoformat(ts)
                now = datetime.now(dt.tzinfo)
            else:
                dt = datetime.fromisoformat(ts.replace("Z", ""))
                now = datetime.utcnow()
            return (now - dt).total_seconds() < days * 86400
        except (ValueError, TypeError):
            return False

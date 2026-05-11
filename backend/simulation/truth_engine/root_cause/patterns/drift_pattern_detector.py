"""
Task 4: DriftPatternDetector — Rule-based recurring failure pattern detection.
No ML. Frequency + correlation analysis only.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import DriftPattern


logger = logging.getLogger('erp.simulation.truth.root_cause.patterns')


class DriftPatternDetector:
    """
    Detects recurring failure patterns across system runs.
    Rule-based detection. No machine learning.
    """

    def __init__(self):
        self._patterns: Dict[str, DriftPattern] = {}

    def detect(
        self,
        mismatch_history: List[Dict[str, Any]],
        current_tick: int,
    ) -> List[DriftPattern]:
        patterns = []
        patterns.extend(self._detect_repeated_inventory_drift(
            mismatch_history, current_tick
        ))
        patterns.extend(self._detect_payment_failure_under_load(
            mismatch_history, current_tick
        ))
        patterns.extend(self._detect_journal_imbalance(
            mismatch_history, current_tick
        ))
        patterns.extend(self._detect_partial_workflow(
            mismatch_history, current_tick
        ))
        patterns.extend(self._detect_concurrent_access(
            mismatch_history, current_tick
        ))
        pattern_map = {}
        for p in patterns:
            if p.pattern_id not in self._patterns:
                self._patterns[p.pattern_id] = p
                pattern_map[p.pattern_id] = p
            else:
                existing = self._patterns[p.pattern_id]
                existing.occurrence_count += 1
                existing.last_seen_tick = current_tick
                existing.frequency = existing.occurrence_count
                existing.matched_mismatch_ids.extend(
                    p.matched_mismatch_ids
                )
                pattern_map[p.pattern_id] = existing
        return list(pattern_map.values())

    def _detect_repeated_inventory_drift(
        self, history: List[Dict[str, Any]], tick: int,
    ) -> List[DriftPattern]:
        inv_mismatches = [
            m for m in history
            if m.get('mismatch_type') == 'inventory_mismatch'
        ]
        if len(inv_mismatches) >= 2:
            return [DriftPattern(
                pattern_id='repeated_inventory_drift',
                pattern_type='repeated_failure',
                description=(
                    "Repeated inventory mismatch after sales operations"
                ),
                affected_module='inventory',
                frequency=len(inv_mismatches),
                matched_mismatch_ids=[m.get('mismatch_id', '')
                                      for m in inv_mismatches],
                first_seen_tick=inv_mismatches[0].get('tick', tick),
                last_seen_tick=tick,
                occurrence_count=len(inv_mismatches),
            )]
        return []

    def _detect_payment_failure_under_load(
        self, history: List[Dict[str, Any]], tick: int,
    ) -> List[DriftPattern]:
        financial = [
            m for m in history
            if m.get('mismatch_type') == 'financial_mismatch'
        ]
        if len(financial) >= 2:
            return [DriftPattern(
                pattern_id='payment_failure_under_load',
                pattern_type='load_sensitive',
                description=(
                    "Payment/journal failure under high load"
                ),
                affected_module='accounting',
                frequency=len(financial),
                matched_mismatch_ids=[m.get('mismatch_id', '')
                                      for m in financial],
                first_seen_tick=financial[0].get('tick', tick),
                last_seen_tick=tick,
                occurrence_count=len(financial),
            )]
        return []

    def _detect_journal_imbalance(
        self, history: List[Dict[str, Any]], tick: int,
    ) -> List[DriftPattern]:
        dupes = [
            m for m in history
            if m.get('mismatch_type') == 'duplicate_entry'
        ]
        if len(dupes) >= 1:
            return [DriftPattern(
                pattern_id='journal_imbalance_concurrency',
                pattern_type='concurrency_related',
                description=(
                    "Journal imbalance detected under concurrent access"
                ),
                affected_module='accounting',
                frequency=len(dupes),
                matched_mismatch_ids=[m.get('mismatch_id', '')
                                      for m in dupes],
                first_seen_tick=dupes[0].get('tick', tick),
                last_seen_tick=tick,
                occurrence_count=len(dupes),
            )]
        return []

    def _detect_partial_workflow(
        self, history: List[Dict[str, Any]], tick: int,
    ) -> List[DriftPattern]:
        incomplete = [
            m for m in history
            if m.get('mismatch_type') == 'workflow_incomplete'
        ]
        if len(incomplete) >= 2:
            return [DriftPattern(
                pattern_id='partial_workflow_execution',
                pattern_type='execution_trend',
                description=(
                    "Partial workflow execution trend detected"
                ),
                affected_module='workflow',
                frequency=len(incomplete),
                matched_mismatch_ids=[m.get('mismatch_id', '')
                                      for m in incomplete],
                first_seen_tick=incomplete[0].get('tick', tick),
                last_seen_tick=tick,
                occurrence_count=len(incomplete),
            )]
        return []

    def _detect_concurrent_access(
        self, history: List[Dict[str, Any]], tick: int,
    ) -> List[DriftPattern]:
        state_drifts = [
            m for m in history
            if m.get('mismatch_type') == 'state_drift'
        ]
        if len(state_drifts) >= 2:
            return [DriftPattern(
                pattern_id='concurrent_access_conflict',
                pattern_type='concurrency_related',
                description=(
                    "Concurrent access conflict causing state drift"
                ),
                affected_module='simulation',
                frequency=len(state_drifts),
                matched_mismatch_ids=[m.get('mismatch_id', '')
                                      for m in state_drifts],
                first_seen_tick=state_drifts[0].get('tick', tick),
                last_seen_tick=tick,
                occurrence_count=len(state_drifts),
            )]
        return []

    def get_all_patterns(self) -> Dict[str, DriftPattern]:
        return dict(self._patterns)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

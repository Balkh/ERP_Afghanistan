"""
TruthEngine — Passive observation orchestrator.
Collects expected vs actual state, compares, scores, reports, snapshots.
NO mutation of ERP. NO correction logic. Read-only observation only.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from simulation.truth_engine.collector.expected import ExpectedStateCollector
from simulation.truth_engine.collector.actual import ActualStateCollector
from simulation.truth_engine.comparator.comparator import TruthComparator
from simulation.truth_engine.scoring.scorer import IntegrityScorer
from simulation.truth_engine.reports.reporter import TruthReportGenerator
from simulation.truth_engine.snapshot.snapshot import SnapshotManager
from simulation.truth_engine.models.models import DriftReport


logger = logging.getLogger('erp.simulation.truth.engine')


class TruthEngine:
    """
    Orchestrates all truth comparison components.
    Passive observer — never mutates production data.
    """

    def __init__(self, max_snapshots: int = 100):
        self._expected_collector: Optional[ExpectedStateCollector] = None
        self._actual_collector = ActualStateCollector()
        self._comparator = TruthComparator()
        self._scorer = IntegrityScorer()
        self._report_generator = TruthReportGenerator()
        self._snapshot_manager = SnapshotManager(max_snapshots=max_snapshots)
        self._last_report: Optional[DriftReport] = None
        self._last_formatted_report: Optional[Dict[str, Any]] = None

    def verify(
        self,
        scenario_id: str,
        tick: int,
        timestamp: Any,
        event_history: List[Any],
        workflow_completions: Dict[str, int],
        agent_executions: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Full verification cycle: collect, compare, score, report, snapshot.
        Returns formatted report dictionary.
        """
        generated_at = datetime.now()
        expected = ExpectedStateCollector.from_event_log(
            scenario_id, tick, timestamp, generated_at,
            event_history, workflow_completions, agent_executions,
        )
        actual = (
            self._actual_collector
            .collect_journal_entries()
            .collect_stock_movements()
            .collect_sales_invoices()
            .collect_purchase_invoices()
            .collect_inventory_quantities()
            .collect_transactions()
            .build()
        )
        report_id = f"truth_{scenario_id}_t{tick}_{uuid.uuid4().hex[:8]}"
        report = self._comparator.compare(
            expected, actual, report_id, scenario_id, tick, generated_at,
        )
        self._comparator.detect_duplicates(actual, report)
        scores = self._scorer.compute_scores(expected, actual,
                                              report.mismatches)
        formatted_report = self._report_generator.generate(report, scores)
        self._snapshot_manager.take_snapshot(
            report_id, scenario_id, tick, timestamp,
            expected, actual,
        )
        self._last_report = report
        self._last_formatted_report = formatted_report
        logger.info(
            "TruthEngine: verification complete for %s tick %d — "
            "%d mismatches, score=%.1f",
            scenario_id, tick, len(report.mismatches),
            scores.get('overall_system_score', 0),
        )
        return formatted_report

    @property
    def last_report(self) -> Optional[DriftReport]:
        return self._last_report

    @property
    def last_formatted_report(self) -> Optional[Dict[str, Any]]:
        return self._last_formatted_report

    @property
    def comparator(self) -> TruthComparator:
        return self._comparator

    @property
    def scorer(self) -> IntegrityScorer:
        return self._scorer

    @property
    def report_generator(self) -> TruthReportGenerator:
        return self._report_generator

    @property
    def snapshot_manager(self) -> SnapshotManager:
        return self._snapshot_manager

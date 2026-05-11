import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from simulation.truth_engine.models.models import (
    Mismatch, MismatchType, MismatchSeverity,
    ExpectedState, ActualState, DriftReport,
)


logger = logging.getLogger('erp.simulation.truth.comparator')


class TruthComparator:
    """
    Compares expected vs actual states.
    Detects mismatches. Classifies divergence types.
    NO automatic fixing. NO silent suppression.
    MUST log every mismatch.
    """

    def __init__(self):
        self._mismatches: List[Mismatch] = []

    def compare(
        self, expected: ExpectedState, actual: ActualState,
        report_id: str, scenario_id: str, tick: int,
        generated_at: datetime,
    ) -> DriftReport:
        self._mismatches = []
        report = DriftReport(report_id, scenario_id, tick,
                             generated_at, expected, actual)
        self._compare_sales(expected, actual, tick, report)
        self._compare_purchases(expected, actual, tick, report)
        self._compare_inventory(expected, actual, tick, report)
        self._compare_workflows(expected, actual, tick, report)
        self._compare_agent_executions(expected, actual, tick, report)
        return report

    def _add_mismatch(self, mismatch: Mismatch):
        self._mismatches.append(mismatch)
        logger.info(
            "TruthComparator: mismatch detected — %s [%s] expected=%s actual=%s",
            mismatch.mismatch_type.value,
            mismatch.severity.value,
            mismatch.expected_value,
            mismatch.actual_value,
        )

    def _compare_sales(self, expected: ExpectedState,
                       actual: ActualState, tick: int,
                       report: DriftReport):
        exp = expected._sales_count
        act = len(actual._invoices)
        if exp != act:
            mismatch = Mismatch(
                mismatch_id=str(uuid.uuid4()),
                mismatch_type=MismatchType.TRANSACTION_MISSING,
                severity=MismatchSeverity.MEDIUM,
                description=(
                    f"Sales count mismatch: expected={exp}, "
                    f"actual={act} at tick {tick}"
                ),
                affected_module='sales',
                timestamp=actual.collected_at,
                expected_value=exp,
                actual_value=act,
                context={'tick': tick},
            )
            self._add_mismatch(mismatch)
            report.add_mismatch(mismatch)

    def _compare_purchases(self, expected: ExpectedState,
                           actual: ActualState, tick: int,
                           report: DriftReport):
        exp = expected._purchase_count
        act = len([i for i in actual._invoices
                   if 'invoice_number' in i])
        if exp != act:
            mismatch = Mismatch(
                mismatch_id=str(uuid.uuid4()),
                mismatch_type=MismatchType.TRANSACTION_MISSING,
                severity=MismatchSeverity.MEDIUM,
                description=(
                    f"Purchase count mismatch: expected={exp}, "
                    f"actual={act} at tick {tick}"
                ),
                affected_module='purchases',
                timestamp=actual.collected_at,
                expected_value=exp,
                actual_value=act,
                context={'tick': tick},
            )
            self._add_mismatch(mismatch)
            report.add_mismatch(mismatch)

    def _compare_inventory(self, expected: ExpectedState,
                           actual: ActualState, tick: int,
                           report: DriftReport):
        for product_id, exp_delta in expected._inventory_delta.items():
            act_qty = actual._inventory_quantity.get(product_id, 0.0)
            if abs(exp_delta - act_qty) > 0.001:
                mismatch = Mismatch(
                    mismatch_id=str(uuid.uuid4()),
                    mismatch_type=MismatchType.INVENTORY_MISMATCH,
                    severity=MismatchSeverity.HIGH,
                    description=(
                        f"Inventory drift for product {product_id}: "
                        f"expected_delta={exp_delta}, "
                        f"actual_qty={act_qty}"
                    ),
                    affected_module='inventory',
                    timestamp=actual.collected_at,
                    expected_value=exp_delta,
                    actual_value=act_qty,
                    context={'product_id': product_id, 'tick': tick},
                )
                self._add_mismatch(mismatch)
                report.add_mismatch(mismatch)

    def _compare_workflows(self, expected: ExpectedState,
                          actual: ActualState, tick: int,
                          report: DriftReport):
        exp_completed = len(expected._workflow_events)
        if exp_completed == 0 and len(actual._journal_entries) > 0:
            mismatch = Mismatch(
                mismatch_id=str(uuid.uuid4()),
                mismatch_type=MismatchType.WORKFLOW_INCOMPLETE,
                severity=MismatchSeverity.LOW,
                description=(
                    "Workflow events expected but journal entries found: "
                    f"journal_count={len(actual._journal_entries)}"
                ),
                affected_module='workflow',
                timestamp=actual.collected_at,
                expected_value=0,
                actual_value=len(actual._journal_entries),
                context={'tick': tick},
            )
            self._add_mismatch(mismatch)
            report.add_mismatch(mismatch)

    def _compare_agent_executions(self, expected: ExpectedState,
                                 actual: ActualState, tick: int,
                                 report: DriftReport):
        if not expected._agent_executions:
            return
        total_expected = sum(expected._agent_executions.values())
        if total_expected > 0 and len(actual._journal_entries) == 0:
            mismatch = Mismatch(
                mismatch_id=str(uuid.uuid4()),
                mismatch_type=MismatchType.STATE_DRIFT,
                severity=MismatchSeverity.LOW,
                description=(
                    f"Agent executions expected ({total_expected}) "
                    f"but no journal entries recorded"
                ),
                affected_module='simulation',
                timestamp=actual.collected_at,
                expected_value=total_expected,
                actual_value=0,
                context={
                    'agent_executions': expected._agent_executions,
                    'tick': tick,
                },
            )
            self._add_mismatch(mismatch)
            report.add_mismatch(mismatch)

    def detect_duplicates(self, actual: ActualState,
                          report: DriftReport):
        seen = set()
        for entry in actual._journal_entries:
            entry_num = entry.get('entry_number', '')
            if entry_num in seen:
                mismatch = Mismatch(
                    mismatch_id=str(uuid.uuid4()),
                    mismatch_type=MismatchType.DUPLICATE_ENTRY,
                    severity=MismatchSeverity.CRITICAL,
                    description=f"Duplicate journal entry: {entry_num}",
                    affected_module='accounting',
                    timestamp=actual.collected_at,
                    expected_value=None,
                    actual_value=entry_num,
                )
                self._add_mismatch(mismatch)
                report.add_mismatch(mismatch)
            seen.add(entry_num)

    @property
    def mismatch_count(self) -> int:
        return len(self._mismatches)

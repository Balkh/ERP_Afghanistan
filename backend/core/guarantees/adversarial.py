"""
Class 7: AdversarialScenarioGenerator — Adversarial Test Expansion.

Generates test scenarios with:
  - Random failure injection (mid-transaction crash)
  - Missing field injection (e.g. company_id null)
  - Duplicate event replay
  - Partial rollback attempt
  - Concurrency conflict simulation
  - Delayed event replay

GUARANTEE: System must fail fast (not silently) for all adversarial inputs.
"""
import random
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import patch


@dataclass
class AdversarialScenario:
    name: str
    description: str
    category: str
    inject_at: Optional[str] = None
    expected_failure_mode: Optional[str] = None


@dataclass
class ScenarioResult:
    scenario: AdversarialScenario
    passed: bool
    failure_detected: bool
    failure_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class AdversarialScenarioGenerator:
    """
    Generates and executes adversarial scenarios.

    Categories:
      - MISSING_FIELD:     Inject null company_id, missing required fields
      - DUPLICATE_EVENT:   Replay the same event twice
      - PARTIAL_ROLLBACK:  Simulate mid-transaction crash
      - CONCURRENCY:       Simulate concurrent modifications
      - DELAYED_EVENT:     Replay events out of order

    Each scenario has an expected_failure_mode — the system must fail
    loudly (raise exception) rather than silently corrupting data.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.results: List[ScenarioResult] = []

    # ── Scenario Factories ──────────────────────────────────────────────

    def generate_missing_field_scenarios(self) -> List[AdversarialScenario]:
        """Generate scenarios that inject null values for required fields."""
        return [
            AdversarialScenario(
                name="null_company_id_on_invoice",
                description="Create SalesInvoice with null company_id",
                category="MISSING_FIELD",
                inject_at="sales.SalesInvoice",
                expected_failure_mode="ValidationError",
            ),
            AdversarialScenario(
                name="null_company_id_on_journal",
                description="Create JournalEntry with null company_id",
                category="MISSING_FIELD",
                inject_at="accounting.JournalEntry",
                expected_failure_mode="ValidationError",
            ),
            AdversarialScenario(
                name="null_company_id_on_return",
                description="Create ReturnOrder with null company_id",
                category="MISSING_FIELD",
                inject_at="returns.ReturnOrder",
                expected_failure_mode="ValidationError",
            ),
            AdversarialScenario(
                name="null_company_id_on_reconciliation",
                description="Create ReconciliationEntry with null company_id",
                category="MISSING_FIELD",
                inject_at="returns.ReconciliationEntry",
                expected_failure_mode="ValidationError",
            ),
        ]

    def generate_duplicate_event_scenarios(self) -> List[AdversarialScenario]:
        """Generate scenarios that replay the same event."""
        return [
            AdversarialScenario(
                name="duplicate_return_approve",
                description="Approve the same ReturnOrder twice",
                category="DUPLICATE_EVENT",
                inject_at="returns.ReturnOrder.approve",
                expected_failure_mode="IntegrityError|ValidationError",
            ),
            AdversarialScenario(
                name="duplicate_journal_post",
                description="Post the same JournalEntry twice",
                category="DUPLICATE_EVENT",
                inject_at="accounting.JournalEntry.post",
                expected_failure_mode="ValidationError",
            ),
            AdversarialScenario(
                name="duplicate_stock_movement",
                description="Create duplicate StockMovement for same batch",
                category="DUPLICATE_EVENT",
                inject_at="inventory.StockMovement",
                expected_failure_mode="IntegrityError",
            ),
        ]

    def generate_partial_rollback_scenarios(self) -> List[AdversarialScenario]:
        """Generate scenarios that simulate mid-transaction crashes."""
        return [
            AdversarialScenario(
                name="crash_after_inventory_before_accounting",
                description="Crash between stock restore and JE creation during return",
                category="PARTIAL_ROLLBACK",
                inject_at="returns.ReturnOrder.approve",
                expected_failure_mode="AtomicBoundaryError",
            ),
            AdversarialScenario(
                name="crash_after_accounting_before_reconciliation",
                description="Crash between JE creation and reconciliation during return",
                category="PARTIAL_ROLLBACK",
                inject_at="returns.ReturnOrder.approve",
                expected_failure_mode="AtomicBoundaryError",
            ),
            AdversarialScenario(
                name="crash_during_sale_dispatch",
                description="Crash mid-way through sales invoice dispatch",
                category="PARTIAL_ROLLBACK",
                inject_at="sales.SalesInvoice.dispatch",
                expected_failure_mode="AtomicBoundaryError",
            ),
        ]

    def generate_concurrency_scenarios(self) -> List[AdversarialScenario]:
        """Generate scenarios simulating concurrent modifications."""
        return [
            AdversarialScenario(
                name="concurrent_batch_update",
                description="Two threads updating same batch simultaneously",
                category="CONCURRENCY",
                inject_at="inventory.Batch.save",
                expected_failure_mode="IntegrityError|OperationalError",
            ),
            AdversarialScenario(
                name="concurrent_invoice_dispatch",
                description="Two threads dispatching same invoice",
                category="CONCURRENCY",
                inject_at="sales.SalesInvoice.dispatch",
                expected_failure_mode="IntegrityError",
            ),
        ]

    def generate_delayed_event_scenarios(self) -> List[AdversarialScenario]:
        """Generate scenarios with out-of-order event replay."""
        return [
            AdversarialScenario(
                name="return_before_invoice",
                description="Create ReturnOrder before its source invoice exists",
                category="DELAYED_EVENT",
                inject_at="returns.ReturnOrder",
                expected_failure_mode="ValidationError",
            ),
            AdversarialScenario(
                name="payment_before_invoice",
                description="Process payment for non-existent invoice",
                category="DELAYED_EVENT",
                inject_at="payments.FinancialTransaction",
                expected_failure_mode="ValidationError",
            ),
        ]

    def generate_all_scenarios(self) -> List[AdversarialScenario]:
        """Generate all adversarial scenarios across all categories."""
        return (
            self.generate_missing_field_scenarios() +
            self.generate_duplicate_event_scenarios() +
            self.generate_partial_rollback_scenarios() +
            self.generate_concurrency_scenarios() +
            self.generate_delayed_event_scenarios()
        )

    # ── Scenario Execution Helpers ──────────────────────────────────────

    def create_with_null_field(self, model_class, field_name: str, **kwargs) -> Any:
        """Force-create a model instance with a null field by bypassing ORM defaults."""
        kwargs[field_name] = None
        return model_class.objects.create(**kwargs)

    @contextmanager
    def inject_failure(self, target: str, side_effect: Callable):
        """Context manager that patches a target with a side effect."""
        with patch(target, side_effect=side_effect) as _p:
            yield _p

    def run_adversarial_test(self, scenario: AdversarialScenario, test_fn: Callable) -> ScenarioResult:
        """Run a single adversarial scenario and return the result."""
        try:
            test_fn(scenario)
            # The test completed without exception — check if that's expected
            if scenario.expected_failure_mode:
                result = ScenarioResult(
                    scenario=scenario,
                    passed=False,
                    failure_detected=False,
                    failure_message=f"Expected failure ({scenario.expected_failure_mode}) but no exception raised",
                )
            else:
                result = ScenarioResult(
                    scenario=scenario,
                    passed=True,
                    failure_detected=False,
                )
        except Exception as e:
            # Check if the exception matches expected failure mode
            exc_name = type(e).__name__
            expected = scenario.expected_failure_mode or ".*"
            if exc_name in expected or any(
                em in str(e) for em in expected.split('|')
            ):
                result = ScenarioResult(
                    scenario=scenario,
                    passed=True,
                    failure_detected=True,
                    failure_message=f"{exc_name}: {e}",
                )
            else:
                result = ScenarioResult(
                    scenario=scenario,
                    passed=False,
                    failure_detected=True,
                    failure_message=f"Unexpected failure: {exc_name}: {e}",
                )
        self.results.append(result)
        return result

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all adversarial test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        by_category: Dict[str, int] = {}
        for r in self.results:
            cat = r.scenario.category
            by_category[cat] = by_category.get(cat, 0) + (1 if r.passed else 0)
        return {
            'total_scenarios': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{passed / total * 100:.1f}%" if total > 0 else "N/A",
            'by_category': by_category,
            'failures': [
                {
                    'name': r.scenario.name,
                    'message': r.failure_message,
                }
                for r in self.results if not r.passed
            ],
        }

    def clear(self) -> None:
        self.results.clear()


_generator_instance: Optional[AdversarialScenarioGenerator] = None


def get_adversarial_generator(seed: int = 42) -> AdversarialScenarioGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AdversarialScenarioGenerator(seed=seed)
    return _generator_instance

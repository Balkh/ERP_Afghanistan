import logging
from enum import Enum
from typing import Any, Dict, List, Optional


logger = logging.getLogger('erp.simulation.truth.models')


class MismatchType(Enum):
    FINANCIAL_MISMATCH = 'financial_mismatch'
    INVENTORY_MISMATCH = 'inventory_mismatch'
    TRANSACTION_MISSING = 'transaction_missing'
    DUPLICATE_ENTRY = 'duplicate_entry'
    WORKFLOW_INCOMPLETE = 'workflow_incomplete'
    STATE_DRIFT = 'state_drift'


class MismatchSeverity(Enum):
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    INFO = 'info'


class Mismatch:
    """
    Immutable mismatch record. No correction, no mutation.
    """

    __slots__ = (
        'mismatch_id', 'mismatch_type', 'severity',
        'expected_value', 'actual_value', 'description',
        'affected_module', 'timestamp', 'context'
    )

    def __init__(
        self,
        mismatch_id: str,
        mismatch_type: MismatchType,
        severity: MismatchSeverity,
        description: str,
        affected_module: str,
        timestamp: Any,
        expected_value: Any = None,
        actual_value: Any = None,
        context: Optional[dict] = None,
    ):
        self.mismatch_id = mismatch_id
        self.mismatch_type = mismatch_type
        self.severity = severity
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.description = description
        self.affected_module = affected_module
        self.timestamp = timestamp
        self.context = dict(context) if context else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mismatch_id': self.mismatch_id,
            'mismatch_type': self.mismatch_type.value,
            'severity': self.severity.value,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value,
            'description': self.description,
            'affected_module': self.affected_module,
            'timestamp': str(self.timestamp),
            'context': dict(self.context),
        }


class ExpectedState:
    """
    Structured expected state snapshot from simulation layer.
    Read-only. No ERP access.
    """

    def __init__(self, scenario_id: str, tick: int,
                 timestamp, collected_at):
        self._scenario_id = scenario_id
        self._tick = tick
        self._timestamp = timestamp
        self._collected_at = collected_at
        self._sales_count: int = 0
        self._purchase_count: int = 0
        self._inventory_delta: Dict[str, float] = {}
        self._returns_count: int = 0
        self._accounting_entries: List[Dict[str, Any]] = []
        self._workflow_events: List[Dict[str, Any]] = []
        self._agent_executions: Dict[str, int] = {}

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def collected_at(self):
        return self._collected_at

    def set_sales_count(self, count: int):
        self._sales_count = count

    def set_purchase_count(self, count: int):
        self._purchase_count = count

    def set_inventory_delta(self, product_id: str, delta: float):
        self._inventory_delta[product_id] = delta

    def set_returns_count(self, count: int):
        self._returns_count = count

    def add_accounting_entry(self, entry: Dict[str, Any]):
        self._accounting_entries.append(dict(entry))

    def add_workflow_event(self, event: Dict[str, Any]):
        self._workflow_events.append(dict(event))

    def set_agent_execution(self, agent_id: str, count: int):
        self._agent_executions[agent_id] = count

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self._scenario_id,
            'tick': self._tick,
            'timestamp': str(self._timestamp),
            'collected_at': str(self._collected_at),
            'sales_count': self._sales_count,
            'purchase_count': self._purchase_count,
            'inventory_delta': dict(self._inventory_delta),
            'returns_count': self._returns_count,
            'accounting_entries': list(self._accounting_entries),
            'workflow_events': list(self._workflow_events),
            'agent_executions': dict(self._agent_executions),
        }


class ActualState:
    """
    Structured actual state from ERP system.
    Read-only snapshot. No mutations.
    """

    def __init__(self, collected_at, source: str = 'erp'):
        self._collected_at = collected_at
        self._source = source
        self._journal_entry_count: int = 0
        self._journal_entries: List[Dict[str, Any]] = []
        self._stock_movements: List[Dict[str, Any]] = []
        self._invoices: List[Dict[str, Any]] = []
        self._inventory_quantity: Dict[str, float] = {}
        self._transactions: List[Dict[str, Any]] = []

    @property
    def collected_at(self):
        return self._collected_at

    @property
    def source(self) -> str:
        return self._source

    def set_journal_count(self, count: int):
        self._journal_entry_count = count

    def add_journal_entry(self, entry: Dict[str, Any]):
        self._journal_entries.append(dict(entry))

    def add_stock_movement(self, movement: Dict[str, Any]):
        self._stock_movements.append(dict(movement))

    def add_invoice(self, invoice: Dict[str, Any]):
        self._invoices.append(dict(invoice))

    def set_inventory_quantity(self, product_id: str, qty: float):
        self._inventory_quantity[product_id] = qty

    def add_transaction(self, txn: Dict[str, Any]):
        self._transactions.append(dict(txn))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'collected_at': str(self._collected_at),
            'source': self._source,
            'journal_entry_count': self._journal_entry_count,
            'journal_entries': list(self._journal_entries),
            'stock_movements': list(self._stock_movements),
            'invoices': list(self._invoices),
            'inventory_quantity': dict(self._inventory_quantity),
            'transactions': list(self._transactions),
        }


class DriftReport:
    """
    Full truth comparison report. Immutable after creation.
    """

    def __init__(self, report_id: str, scenario_id: str,
                 tick: int, generated_at,
                 expected: ExpectedState, actual: ActualState):
        self._report_id = report_id
        self._scenario_id = scenario_id
        self._tick = tick
        self._generated_at = generated_at
        self._expected = expected
        self._actual = actual
        self._mismatches: List[Mismatch] = []
        self._scores: Dict[str, float] = {}

    def add_mismatch(self, mismatch: Mismatch):
        self._mismatches.append(mismatch)

    def set_score(self, metric: str, score: float):
        self._scores[metric] = score

    @property
    def report_id(self) -> str:
        return self._report_id

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def generated_at(self):
        return self._generated_at

    @property
    def mismatches(self) -> List[Mismatch]:
        return list(self._mismatches)

    @property
    def scores(self) -> Dict[str, float]:
        return dict(self._scores)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self._report_id,
            'scenario_id': self._scenario_id,
            'tick': self._tick,
            'generated_at': str(self._generated_at),
            'expected': self._expected.to_dict(),
            'actual': self._actual.to_dict(),
            'mismatches': [m.to_dict() for m in self._mismatches],
            'scores': dict(self._scores),
            'mismatch_count': len(self._mismatches),
        }
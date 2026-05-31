"""
Class 4: DeterministicReplayValidator — Replay Determinism Guarantee.

GUARANTEE: Same inputs → same ledger. Same sequence → same balances.
Same events → same inventory state.

Provides:
  - State hashing at checkpoints
  - Replay comparison between two runs
  - Determinism verification for any queryset
"""
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


@dataclass
class StateCheckpoint:
    label: str
    checksum: str
    details: Dict[str, Any] = field(default_factory=dict)

    def matches(self, other: 'StateCheckpoint') -> bool:
        return self.checksum == other.checksum


@dataclass
class ReplayComparison:
    label: str
    match: bool
    first_checksum: str
    second_checksum: str
    differences: List[str] = field(default_factory=list)


class DeterministicReplayValidator:
    """
    Validates that the system produces deterministic results.

    Usage:
        validator = DeterministicReplayValidator()
        cp1 = validator.checkpoint('AR Balance', ar_queryset)
        cp2 = validator.checkpoint('AP Balance', ap_queryset)
        results = validator.compare('Run 1', 'Run 2', [cp1, cp2])
    """

    def __init__(self):
        self.history: Dict[str, List[StateCheckpoint]] = OrderedDict()

    def _checksum(self, data: Dict[str, Any]) -> str:
        """Generate a deterministic checksum from a dictionary."""
        raw = json.dumps(data, sort_keys=True, cls=DecimalEncoder)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    def checkpoint(self, label: str, queryset_or_value) -> StateCheckpoint:
        """
        Create a checkpoint from a queryset or a dict.
        For querysets: orders by PK to ensure deterministic iteration,
        then hashes all field values.
        """
        if hasattr(queryset_or_value, 'order_by'):
            qs = queryset_or_value.order_by('id')
            values = list(qs.values())
            data = {label: values}
        else:
            data = {label: queryset_or_value}

        details = data
        checksum = self._checksum(data)
        cp = StateCheckpoint(label=label, checksum=checksum, details=details)
        return cp

    def record_run(self, run_label: str, checkpoints: List[StateCheckpoint]) -> None:
        """Store all checkpoints for a given run label."""
        self.history[run_label] = checkpoints

    def compare(self, run_a: str, run_b: str) -> List[ReplayComparison]:
        """Compare all checkpoints between two runs."""
        results: List[ReplayComparison] = []
        a_cps = self.history.get(run_a, [])
        b_cps = self.history.get(run_b, [])

        a_map = {cp.label: cp for cp in a_cps}
        b_map = {cp.label: cp for cp in b_cps}

        all_labels = set(a_map.keys()) | set(b_map.keys())
        for label in sorted(all_labels):
            cp_a = a_map.get(label)
            cp_b = b_map.get(label)
            if cp_a is None or cp_b is None:
                results.append(ReplayComparison(
                    label=label,
                    match=False,
                    first_checksum=cp_a.checksum if cp_a else 'MISSING',
                    second_checksum=cp_b.checksum if cp_b else 'MISSING',
                    differences=[f"Checkpoint missing in one run: '{label}'"]
                ))
                continue

            differences = self._find_differences(cp_a.details, cp_b.details)
            results.append(ReplayComparison(
                label=label,
                match=cp_a.matches(cp_b),
                first_checksum=cp_a.checksum,
                second_checksum=cp_b.checksum,
                differences=differences,
            ))
        return results

    def _find_differences(self, a: Dict, b: Dict) -> List[str]:
        """Find differences between two checkpoint dicts."""
        diffs = []
        for key in set(list(a.keys()) + list(b.keys())):
            if key not in a:
                diffs.append(f"Key '{key}' missing in first run")
            elif key not in b:
                diffs.append(f"Key '{key}' missing in second run")
            elif a[key] != b[key]:
                diffs.append(f"Value differs for '{key}': {a[key]} vs {b[key]}")
        return diffs

    def verify_determinism(self, run_label: str) -> bool:
        """
        Verify that running the same simulation twice produces identical results.
        Requires at least 2 recorded runs.
        """
        if len(self.history) < 2:
            return True
        runs = list(self.history.keys())
        comparisons = self.compare(runs[-2], runs[-1])
        return all(c.match for c in comparisons)

    def assert_deterministic(self, run_a: str, run_b: str) -> None:
        """Assert that two runs are deterministic (identical checkpoints)."""
        comparisons = self.compare(run_a, run_b)
        failures = [c for c in comparisons if not c.match]
        if failures:
            msgs = []
            for f in failures:
                msgs.append(
                    f"  {f.label}: {f.first_checksum} vs {f.second_checksum} — "
                    f"{'; '.join(f.differences)}"
                )
            raise AssertionError(
                f"REPLAY DETERMINISM VIOLATION ({len(failures)} mismatches):\n" +
                "\n".join(msgs)
            )


_validator_instance: Optional[DeterministicReplayValidator] = None


def get_replay_validator() -> DeterministicReplayValidator:
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DeterministicReplayValidator()
    return _validator_instance

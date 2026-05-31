"""
Section 8 — Coverage Baseline Snapshots.
Stores and compares coverage baselines over time.
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from test_governance.weighted_coverage import CoverageResult


@dataclass
class BaselineEntry:
    timestamp: str
    raw_coverage: float
    weighted_coverage: float
    critical_path_coverage: float
    risk_adjusted_score: float
    tier_breakdown: Dict
    untested_critical: List[str]


class BaselineTracker:

    def __init__(self, baseline_dir: str = "test_governance/reports"):
        self._baseline_dir = baseline_dir
        self._baseline_file = os.path.join(baseline_dir, "coverage_baseline.json")
        os.makedirs(baseline_dir, exist_ok=True)

    def take_snapshot(self, result: CoverageResult) -> BaselineEntry:
        return BaselineEntry(
            timestamp=datetime.utcnow().isoformat(),
            raw_coverage=result.raw_coverage,
            weighted_coverage=result.weighted_coverage,
            critical_path_coverage=result.critical_path_coverage,
            risk_adjusted_score=result.risk_adjusted_score,
            tier_breakdown=result.tier_breakdown,
            untested_critical=result.untested_critical,
        )

    def save_baseline(self, result: CoverageResult) -> None:
        entry = self.take_snapshot(result)
        history = self._load_history()
        history.append({
            "timestamp": entry.timestamp,
            "raw_coverage": entry.raw_coverage,
            "weighted_coverage": entry.weighted_coverage,
            "critical_path_coverage": entry.critical_path_coverage,
            "risk_adjusted_score": entry.risk_adjusted_score,
            "tier_breakdown": entry.tier_breakdown,
            "untested_critical": entry.untested_critical,
        })
        with open(self._baseline_file, "w") as f:
            json.dump(history, f, indent=2)

    def _load_history(self) -> List[Dict]:
        if not os.path.exists(self._baseline_file):
            return []
        with open(self._baseline_file, "r") as f:
            return json.load(f)

    def get_latest(self) -> Optional[BaselineEntry]:
        history = self._load_history()
        if not history:
            return None
        latest = history[-1]
        return BaselineEntry(**latest)

    def get_history(self) -> List[Dict]:
        return self._load_history()

    def compare(self, current: CoverageResult) -> Dict:
        latest = self.get_latest()
        if not latest:
            return {"status": "first_baseline", "message": "No prior baseline to compare"}
        deltas = {
            "raw_coverage": round(current.raw_coverage - latest.raw_coverage, 2),
            "weighted_coverage": round(current.weighted_coverage - latest.weighted_coverage, 2),
            "critical_path_coverage": round(current.critical_path_coverage - latest.critical_path_coverage, 2),
            "risk_adjusted_score": round(current.risk_adjusted_score - latest.risk_adjusted_score, 2),
        }
        regression = any(v < -2.0 for v in deltas.values())
        critical_regression = current.critical_path_coverage < latest.critical_path_coverage - 5.0
        return {
            "status": "regression_detected" if regression else "stable",
            "deltas": deltas,
            "prior_timestamp": latest.timestamp,
            "critical_regression": critical_regression,
            "message": "Critical coverage regression detected" if critical_regression
            else "Coverage stable or improving",
        }

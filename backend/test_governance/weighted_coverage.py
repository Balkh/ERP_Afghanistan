"""
Section 2 — Weighted Coverage Engine.
Computes weighted and critical-path coverage from coverage.py JSON report.
"""
import json
import os
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass

from test_governance.critical_registry import (
    REGISTRY, PathTier, TIER_ORDER, CriticalPathRegistry,
)


TIER_WEIGHTS = {
    PathTier.CRITICAL: 10.0,
    PathTier.HIGH: 5.0,
    PathTier.NORMAL: 2.0,
    PathTier.LOW: 0.5,
}

TIER_MINIMUMS = {
    PathTier.CRITICAL: 85.0,
    PathTier.HIGH: 65.0,
    PathTier.NORMAL: 35.0,
    PathTier.LOW: 0.0,
}


@dataclass
class ModuleCoverage:
    name: str
    tier: str
    covered_lines: int
    total_lines: int
    coverage_pct: float
    weight: float

    @property
    def weighted_pct(self) -> float:
        return self.coverage_pct * self.weight

    @property
    def meets_minimum(self) -> bool:
        min_val = TIER_MINIMUMS.get(self.tier, 0.0)
        return self.coverage_pct >= min_val


@dataclass
class CoverageResult:
    raw_coverage: float
    weighted_coverage: float
    critical_path_coverage: float
    untested_critical: List[str]
    risk_adjusted_score: float
    tier_breakdown: Dict[str, Dict]
    module_results: List[ModuleCoverage]


class WeightedCoverageEngine:

    def __init__(self, registry: Optional[CriticalPathRegistry] = None):
        self._registry = registry or REGISTRY

    def load_coverage_json(self, path: str) -> Dict:
        with open(path, "r") as f:
            return json.load(f)

    def parse_module_name(self, file_path: str) -> str:
        """Extract module name from coverage file path."""
        parts = file_path.replace("\\", "/").split("/")
        if len(parts) >= 2 and parts[0] == "core" and len(parts) >= 3:
            return f"core.{parts[1]}"
        if len(parts) >= 1:
            return parts[0]
        return "unknown"

    def compute(self, coverage_data: Dict) -> CoverageResult:
        total_covered = 0
        total_statements = 0
        weighted_sum = 0.0
        weight_sum = 0.0
        critical_sum = 0.0
        critical_count = 0
        untested_critical: List[str] = []
        module_results: List[ModuleCoverage] = []
        tier_data: Dict[str, Dict] = {}

        for file_path, file_data in coverage_data.get("files", {}).items():
            summary = file_data.get("summary", {})
            covered = summary.get("covered_lines", 0)
            missing = summary.get("missing_lines", 0)
            total = covered + missing
            if total == 0:
                continue

            module_name = self.parse_module_name(file_path)
            tier = self._registry.get_tier(module_name)
            pct = (covered / total) * 100.0
            weight = TIER_WEIGHTS.get(tier, 1.0)

            mc = ModuleCoverage(
                name=module_name,
                tier=tier,
                covered_lines=covered,
                total_lines=total,
                coverage_pct=round(pct, 2),
                weight=weight,
            )
            module_results.append(mc)

            total_covered += covered
            total_statements += total
            weighted_sum += pct * weight
            weight_sum += weight

            if tier == PathTier.CRITICAL:
                critical_sum += pct
                critical_count += 1
                if pct < TIER_MINIMUMS[PathTier.CRITICAL]:
                    untested_critical.append(module_name)

            if tier not in tier_data:
                tier_data[tier] = {"total_pct": 0.0, "count": 0, "pass": 0, "fail": 0}
            tier_data[tier]["total_pct"] += pct
            tier_data[tier]["count"] += 1
            if mc.meets_minimum:
                tier_data[tier]["pass"] += 1
            else:
                tier_data[tier]["fail"] += 1

        raw_coverage = (total_covered / total_statements * 100.0) if total_statements > 0 else 0.0
        weighted_coverage = (weighted_sum / weight_sum) if weight_sum > 0 else 0.0
        critical_path_coverage = (critical_sum / critical_count) if critical_count > 0 else 0.0

        risk_adjusted_score = weighted_coverage * 0.7 + critical_path_coverage * 0.3
        if untested_critical:
            risk_adjusted_score *= 0.8

        tier_breakdown = {}
        for tier, data in tier_data.items():
            avg = data["total_pct"] / data["count"] if data["count"] > 0 else 0
            tier_breakdown[tier] = {
                "average_coverage": round(avg, 2),
                "module_count": data["count"],
                "meeting_minimum": data["pass"],
                "below_minimum": data["fail"],
            }

        return CoverageResult(
            raw_coverage=round(raw_coverage, 2),
            weighted_coverage=round(weighted_coverage, 2),
            critical_path_coverage=round(critical_path_coverage, 2),
            untested_critical=untested_critical,
            risk_adjusted_score=round(risk_adjusted_score, 2),
            tier_breakdown=tier_breakdown,
            module_results=module_results,
        )

    def compute_from_htmlcov(self, htmlcov_dir: str = "htmlcov") -> Optional[CoverageResult]:
        """Load coverage.json from htmlcov directory."""
        path = os.path.join(htmlcov_dir, "coverage.json")
        if not os.path.exists(path):
            return None
        data = self.load_coverage_json(path)
        return self.compute(data)

    def compute_from_file(self, path: str) -> Optional[CoverageResult]:
        if not os.path.exists(path):
            return None
        data = self.load_coverage_json(path)
        return self.compute(data)

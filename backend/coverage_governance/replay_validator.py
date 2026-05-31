"""
Phase 7 — Replay + Determinism Coverage Validator.
Validates replay consistency, snapshot checksums, event ordering,
and audit reproducibility.
"""

import os
import re
from typing import Dict, List, Optional, Set

from coverage_governance.models import ReplayDeterminismResult


TEST_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "simulation", "tests")),
]


class ReplayDeterminismValidator:

    def validate(self) -> ReplayDeterminismResult:
        test_files = self._discover_test_files()
        test_functions = self._extract_all_test_functions(test_files)

        replay_tests = set()
        snapshot_tests = set()
        determinism_tests = set()
        event_order_tests = set()
        replay_modules: Set[str] = set()
        total_replay = 0

        for fname, functions in test_functions.items():
            for fn in functions:
                fn_lower = fn.lower()
                fp_lower = fname.lower()

                if "replay" in fn_lower or "replay" in fp_lower:
                    replay_tests.add(fn)
                    total_replay += 1
                    if "snapshot" in fp_lower or "snapshot" in fn_lower:
                        snapshot_tests.add(fn)
                    if "determin" in fn_lower:
                        determinism_tests.add(fn)
                    if "order" in fn_lower or "sequence" in fn_lower:
                        event_order_tests.add(fn)
                    if "audit" in fn_lower or "audit" in fp_lower:
                        replay_modules.add("core.audit")
                    elif "runner" in fp_lower or "runner" in fn_lower:
                        replay_modules.add("core.runner")
                    elif "simulation" in fp_lower:
                        replay_modules.add("simulation")
                    else:
                        replay_modules.add("unknown")

        has_replay_checksum = bool(re.search(
            r"test_replay_checksum|test_snapshot_verif|test_checksum",
            str(test_functions)
        ))

        has_snapshot_verif = bool(snapshot_tests)
        has_deterministic = bool(determinism_tests)
        has_event_order = bool(event_order_tests)

        replay_score = 0.0
        if total_replay >= 10:
            replay_score = 100.0
        elif total_replay >= 5:
            replay_score = 75.0
        elif total_replay >= 2:
            replay_score = 50.0
        elif total_replay >= 1:
            replay_score = 25.0

        determinism_score = 0.0
        if has_deterministic and has_replay_checksum and has_snapshot_verif:
            determinism_score = 100.0
        elif has_deterministic and has_snapshot_verif:
            determinism_score = 75.0
        elif has_replay_checksum or has_snapshot_verif:
            determinism_score = 50.0
        elif total_replay > 0:
            determinism_score = 25.0

        auditability_score = 0.0
        if "core.audit" in replay_modules and has_event_order:
            auditability_score = 100.0
        elif "core.audit" in replay_modules:
            auditability_score = 75.0
        elif "core.runner" in replay_modules:
            auditability_score = 50.0
        elif total_replay > 0:
            auditability_score = 25.0

        return ReplayDeterminismResult(
            replay_checksum_tests_found=has_replay_checksum,
            snapshot_verification_tests_found=has_snapshot_verif,
            deterministic_replay_tests_found=has_deterministic,
            event_ordering_tests_found=has_event_order,
            replay_modules_tested=replay_modules,
            total_replay_tests=total_replay,
            replay_coverage_score=replay_score,
            determinism_score=determinism_score,
            auditability_score=auditability_score,
        )

    def _discover_test_files(self) -> List[str]:
        files = []
        for d in TEST_DIRS:
            if os.path.isdir(d):
                for root, _, filenames in os.walk(d):
                    for fn in filenames:
                        if fn.startswith("test_") and fn.endswith(".py"):
                            files.append(os.path.join(root, fn))
        return files

    def _extract_all_test_functions(self, files: List[str]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for fp in files:
            fname = os.path.basename(fp)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            functions = re.findall(r"def (test_\w+)\s*\(", content)
            if functions:
                result[fname] = functions
        return result

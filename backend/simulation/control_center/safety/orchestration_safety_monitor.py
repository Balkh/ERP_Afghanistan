"""Orchestration safety monitor that coordinates all safety guards."""
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.control_center.models import SafetyReport
from simulation.control_center.safety.recursion_guard import RecursionGuard
from simulation.control_center.safety.graph_explosion_guard import GraphExplosionGuard
from simulation.control_center.safety.memory_pressure_guard import MemoryPressureGuard


class OrchestrationSafetyMonitor:
    """Coordinates recursion, graph, and memory safety checks."""

    def __init__(self, max_reports: int = 100):
        self._reports: deque = deque(maxlen=max_reports)
        self._recursion_guard: Optional[RecursionGuard] = None
        self._graph_guard: Optional[GraphExplosionGuard] = None
        self._memory_guard: Optional[MemoryPressureGuard] = None

    def init_subcomponents(
        self,
        recursion_guard: RecursionGuard,
        graph_guard: GraphExplosionGuard,
        memory_guard: MemoryPressureGuard,
    ) -> None:
        try:
            self._recursion_guard = recursion_guard
            self._graph_guard = graph_guard
            self._memory_guard = memory_guard
        except Exception:
            pass

    def perform_safety_check(
        self,
        report_id: str,
        current_depth: int,
        node_count: int,
        edge_count: int,
        container_sizes: Dict[str, int],
        container_maxlens: Dict[str, int],
        context: str = "",
    ) -> SafetyReport:
        try:
            violations: List[str] = []
            details: Dict[str, Any] = {}

            if self._recursion_guard:
                depth_result = self._recursion_guard.check_depth(current_depth, context)
                details["recursion"] = depth_result
                if depth_result.get("violation"):
                    violations.append(
                        f"Recursion depth {current_depth} exceeds max {self._recursion_guard.get_max_depth()}"
                    )

            if self._graph_guard:
                graph_result = self._graph_guard.check_graph_size(
                    node_count, edge_count, context
                )
                details["graph"] = graph_result
                if not graph_result.get("safe", True):
                    violations.extend(graph_result.get("violations", []))

            if self._memory_guard:
                memory_result = self._memory_guard.check_pressure(
                    container_sizes, container_maxlens
                )
                details["memory"] = memory_result
                if not memory_result.get("safe", True):
                    violations.extend(memory_result.get("violations", []))

            is_safe = len(violations) == 0
            memory_pressure = details.get("memory", {}).get("pressure", 0.0)

            report = SafetyReport(
                report_id=report_id,
                is_safe=is_safe,
                recursion_depth=current_depth,
                graph_size=node_count + edge_count,
                memory_pressure=memory_pressure,
                violations=violations,
                details=details,
            )
            self._reports.append(report)
            return report
        except Exception:
            error_report = SafetyReport(
                report_id=report_id,
                is_safe=False,
                recursion_depth=current_depth,
                graph_size=node_count + edge_count,
                memory_pressure=1.0,
                violations=["perform_safety_check failed with unexpected error"],
                details={"error": True},
            )
            try:
                self._reports.append(error_report)
            except Exception:
                pass
            return error_report

    def get_report(self, report_id: str) -> Optional[SafetyReport]:
        try:
            for report in self._reports:
                if report.report_id == report_id:
                    return report
            return None
        except Exception:
            return None

    def get_latest_report(self) -> Optional[SafetyReport]:
        try:
            if self._reports:
                return self._reports[-1]
            return None
        except Exception:
            return None

    def get_all_reports(self) -> List[SafetyReport]:
        try:
            return list(self._reports)
        except Exception:
            return []

    def get_report_count(self) -> int:
        try:
            return len(self._reports)
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self._reports.clear()
            if self._recursion_guard:
                self._recursion_guard.clear()
            if self._graph_guard:
                self._graph_guard.clear()
            if self._memory_guard:
                self._memory_guard.clear()
        except Exception:
            pass

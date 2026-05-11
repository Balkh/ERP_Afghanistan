"""
Task E: SimulationLoadAnalyzer — measures tick execution, orchestration, graph costs.
"""
import logging
import time
from typing import Any, Dict, List

from simulation.truth_engine.root_cause.models import CausalGraph

logger = logging.getLogger('erp.simulation.audit.performance.analyzer')


class SimulationLoadAnalyzer:
    MEASUREMENT_SAMPLES = 3

    def measure_tick_cost(self, tick_fn, *args, **kwargs) -> Dict[str, float]:
        times = []
        for _ in range(self.MEASUREMENT_SAMPLES):
            start = time.monotonic()
            tick_fn(*args, **kwargs)
            elapsed = time.monotonic() - start
            times.append(elapsed)
        avg = sum(times) / len(times)
        return {
            'avg_seconds': round(avg, 6),
            'min_seconds': round(min(times), 6),
            'max_seconds': round(max(times), 6),
            'samples': self.MEASUREMENT_SAMPLES,
        }

    def measure_orchestration_cost(self, workfn) -> Dict[str, float]:
        times = []
        for _ in range(self.MEASUREMENT_SAMPLES):
            start = time.monotonic()
            workfn()
            elapsed = time.monotonic() - start
            times.append(elapsed)
        avg = sum(times) / len(times)
        return {
            'avg_seconds': round(avg, 6),
            'min_seconds': round(min(times), 6),
            'max_seconds': round(max(times), 6),
        }

    def estimate_graph_traversal(self, graph: CausalGraph) -> Dict[str, Any]:
        nodes = graph.nodes
        edges = graph.edges
        node_count = len(nodes)
        edge_count = len(edges)
        estimated_cost_ms = (node_count + edge_count) * 0.001
        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'estimated_traversal_cost_ms': round(estimated_cost_ms, 4),
            'cost_warning': estimated_cost_ms > 100.0,
        }

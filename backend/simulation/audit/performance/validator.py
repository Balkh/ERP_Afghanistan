"""
Task E: StabilityThresholdValidator — validates thresholds and generates warnings.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger('erp.simulation.audit.performance.validator')


class StabilityThresholdValidator:
    LATENCY_THRESHOLD_MS = 100.0
    GRAPH_TRAVERSAL_THRESHOLD_MS = 50.0
    EVENT_PROCESSING_THRESHOLD_MS = 10.0

    def validate(self, tick_cost: Dict[str, float],
                 graph_cost: Dict[str, Any]) -> Dict[str, Any]:
        warnings = []
        if tick_cost.get('avg_seconds', 0) * 1000 > self.LATENCY_THRESHOLD_MS:
            warnings.append(
                f"Tick latency exceeds {self.LATENCY_THRESHOLD_MS}ms"
            )
        if graph_cost.get('estimated_traversal_cost_ms', 0) > \
                self.GRAPH_TRAVERSAL_THRESHOLD_MS:
            warnings.append(
                f"Graph traversal cost exceeds "
                f"{self.GRAPH_TRAVERSAL_THRESHOLD_MS}ms"
            )
        return {
            'threshold_warnings': warnings,
            'warning_count': len(warnings),
            'latency_within_bounds': len([w for w in warnings
                                          if 'latency' in w]) == 0,
            'graph_within_bounds': len([w for w in warnings
                                        if 'Graph' in w]) == 0,
        }

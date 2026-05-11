"""
Task C: StoragePressureAnalyzer — estimates memory growth and scaling risks.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.audit.memory.analyzer')


class StoragePressureAnalyzer:
    def estimate(self, structure_sizes: Dict[str, int],
                 max_limits: Dict[str, int],
                 tick_count: int = 0) -> Dict[str, Any]:
        warnings = {}
        growth_trends = {}
        for name, current_size in structure_sizes.items():
            limit = max_limits.get(name, float('inf'))
            usage_pct = (current_size / limit * 100.0) if limit else 0.0
            warnings[name] = {
                'current': current_size,
                'limit': limit,
                'usage_percent': round(usage_pct, 2),
                'warning': usage_pct > 80.0,
            }
            if tick_count > 0:
                growth_per_tick = current_size / max(tick_count, 1)
                growth_trends[name] = round(growth_per_tick, 4)
        return {
            'growth_warnings': warnings,
            'growth_per_tick': growth_trends,
            'has_pressure': any(
                w.get('warning', False) for w in warnings.values()
            ),
        }

"""Drift visualization data builder for time series visualization.

Strictly read-only, bounded memory, exception-safe.
"""
from collections import deque
from typing import Any, Dict, List, Optional


class DriftVisualization:
    """Builder for drift visualization time series data.
    
    Uses bounded deque for drift data points. All operations are exception-safe.
    """

    def __init__(self, max_data_points: int = 500):
        """Initialize the drift visualization with bounded data point storage.
        
        Args:
            max_data_points: Maximum number of drift points to retain. Defaults to 500.
        """
        self._max_data_points = max(max_data_points, 1)
        self._drift_points: deque = deque(maxlen=self._max_data_points)

    def record_drift_point(
        self,
        tick: int,
        drift_type: str,
        severity: str,
        value: float,
        source: str = ""
    ) -> Dict[str, Any]:
        """Record a drift data point and return it.
        
        Args:
            tick: Simulation tick when drift was observed.
            drift_type: Type of drift (e.g., 'inventory', 'financial', 'latency').
            severity: Severity level ('info', 'low', 'medium', 'high', 'critical').
            value: Numeric drift value.
            source: Optional source identifier (e.g., phase name).
            
        Returns:
            Dict containing the recorded point data.
        """
        try:
            point = {
                'tick': int(tick),
                'drift_type': str(drift_type).lower(),
                'severity': str(severity).lower(),
                'value': float(value),
                'source': str(source) if source else ""
            }
            
            self._drift_points.append(point.copy())
            
            return point
        except Exception:
            return {
                'tick': 0,
                'drift_type': 'unknown',
                'severity': 'unknown',
                'value': 0.0,
                'source': ''
            }

    def build_drift_series(
        self,
        drift_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Build time series data for drift visualization.
        
        Filters points by type and/or source if provided, returns sorted by tick.
        
        Args:
            drift_type: Optional filter by drift type. If None, include all.
            source: Optional filter by source. If None, include all.
            limit: Maximum number of points to return. Defaults to 100.
            
        Returns:
            Dict with: series (list of {tick, value}), type, source, data_points count.
        """
        try:
            limit = max(1, int(limit))
            filtered: List[Dict[str, Any]] = []
            
            target_type = str(drift_type).lower() if drift_type else None
            target_source = str(source) if source else None
            
            for point in self._drift_points:
                if target_type is not None and point['drift_type'] != target_type:
                    continue
                if target_source is not None and point['source'] != target_source:
                    continue
                filtered.append(point)
            
            filtered_sorted = sorted(filtered, key=lambda p: p['tick'])
            
            if len(filtered_sorted) > limit:
                filtered_sorted = filtered_sorted[-limit:]
            
            series = [{'tick': p['tick'], 'value': p['value']} for p in filtered_sorted]
            
            return {
                'series': series,
                'type': target_type if target_type else 'all',
                'source': target_source if target_source else 'all',
                'data_points': len(series)
            }
        except Exception:
            return {
                'series': [],
                'type': drift_type if drift_type else 'all',
                'source': source if source else 'all',
                'data_points': 0
            }

    def get_drift_data_point_count(self) -> int:
        """Get the current number of stored drift data points.
        
        Returns:
            Count of drift points in storage.
        """
        try:
            return len(self._drift_points)
        except Exception:
            return 0

    def clear(self) -> None:
        """Clear all stored drift data points."""
        try:
            self._drift_points.clear()
        except Exception:
            pass

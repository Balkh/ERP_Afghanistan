"""Operational heatmap builder for signal distribution visualization.

Strictly read-only, bounded memory, exception-safe.
"""
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.control_center.models import OperationalSignal


class OperationalHeatmap:
    """Builder for operational heatmaps showing signal distribution.
    
    Uses bounded deque for cell data storage. All operations are exception-safe.
    """

    def __init__(self, max_cells: int = 500):
        """Initialize the heatmap with bounded cell storage.
        
        Args:
            max_cells: Maximum number of cell data entries to retain. Defaults to 500.
        """
        self._max_cells = max(max_cells, 1)
        self._cell_history: deque = deque(maxlen=self._max_cells)

    def build_heatmap(
        self,
        signals: List[OperationalSignal],
        sources: Optional[List[str]] = None,
        severities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build a heatmap grid of source × severity counts.
        
        Args:
            signals: List of OperationalSignal instances to analyze.
            sources: Optional list of source names to include. If None, auto-detect.
            severities: Optional list of severities to include. If None, use standard set.
            
        Returns:
            Dict with: grid (list of {source, severity, count}), total_signals,
            unique_sources, unique_severities.
        """
        try:
            standard_severities = ['info', 'low', 'medium', 'high', 'critical']
            
            if severities is None:
                target_severities = standard_severities
            else:
                target_severities = [str(s).lower() for s in severities]
            
            source_set: set = set()
            if sources is not None:
                source_set.update(str(s) for s in sources)
            
            grid_data: Dict[tuple, int] = {}
            
            if signals:
                for signal in signals:
                    try:
                        source = str(signal.source_phase)
                        severity = signal.severity.value if hasattr(signal.severity, 'value') else str(signal.severity).lower()
                        
                        if sources is not None and source not in source_set:
                            continue
                        if severity not in target_severities:
                            continue
                        
                        key = (source, severity)
                        grid_data[key] = grid_data.get(key, 0) + 1
                        source_set.add(source)
                    except Exception:
                        continue
            
            grid: List[Dict[str, Any]] = []
            for source in sorted(source_set):
                for severity in target_severities:
                    count = grid_data.get((source, severity), 0)
                    cell = {'source': source, 'severity': severity, 'count': count}
                    grid.append(cell)
                    
                    if len(self._cell_history) < self._max_cells:
                        self._cell_history.append(cell.copy())
            
            total_signals = sum(grid_data.values())
            unique_sources = len(source_set)
            unique_severities = len(target_severities)
            
            return {
                'grid': grid,
                'total_signals': total_signals,
                'unique_sources': unique_sources,
                'unique_severities': unique_severities
            }
        except Exception:
            return {
                'grid': [],
                'total_signals': 0,
                'unique_sources': 0,
                'unique_severities': 0
            }

    def get_heatmap_cells(self) -> List[Dict[str, Any]]:
        """Get all stored heatmap cell history.
        
        Returns:
            List of cell dicts with source, severity, count.
        """
        try:
            return list(self._cell_history)
        except Exception:
            return []

    def clear(self) -> None:
        """Clear all stored cell history."""
        try:
            self._cell_history.clear()
        except Exception:
            pass

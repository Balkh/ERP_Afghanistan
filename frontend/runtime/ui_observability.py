"""
Phase UX.5 — Frontend UI Observability.

Lightweight, opt-in runtime diagnostics for UI performance.
Detects slow screens, signal storms, repaint issues, and widget creation costs.

All metrics are in-memory, bounded, and NEVER affect runtime performance.
"""
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Tuple


_MAX_SIGNAL_EVENTS = 200
_MAX_REPAINT_RECORDS = 100
_MAX_WIDGET_COST_RECORDS = 100

_SIGNAL_STORM_THRESHOLD = 50  # signals per second
_SLOW_SCREEN_MS = 3000        # threshold from logger.py
_SLOW_DIALOG_MS = 5000
_SLOW_WIDGET_MS = 500
_SLOW_TABLE_MS = 200


class _SignalStormDetector:
    """Detects excessive signal emissions that may indicate storms."""

    def __init__(self):
        self._lock = threading.Lock()
        self._signal_log: deque = deque(maxlen=_MAX_SIGNAL_EVENTS)
        self._signal_counts: Dict[str, int] = defaultdict(int)
        self._storms_detected: int = 0

    def record_signal(self, signal_name: str, source: str = ""):
        now = time.time()
        with self._lock:
            self._signal_log.append({
                'signal': signal_name, 'source': source, 'ts': now
            })
            self._signal_counts[signal_name] += 1

    def check_storm(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            cutoff = now - 1.0
            recent = [e for e in self._signal_log if e['ts'] > cutoff]
            if len(recent) >= _SIGNAL_STORM_THRESHOLD:
                # Count by signal type
                by_type: Dict[str, int] = defaultdict(int)
                for e in recent:
                    by_type[e['signal']] += 1
                top_signals = sorted(by_type.items(), key=lambda x: -x[1])[:5]
                self._storms_detected += 1
                return {
                    'total_signals_per_sec': len(recent),
                    'top_signals': top_signals,
                    'timestamp': now,
                    'storms_detected_total': self._storms_detected,
                }
        return None

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_signals_tracked': len(self._signal_log),
                'unique_signal_types': len(self._signal_counts),
                'signal_type_counts': dict(self._signal_counts),
                'storms_detected': self._storms_detected,
            }


class _RepaintMonitor:
    """Tracks paint event frequency per widget type."""

    def __init__(self):
        self._lock = threading.Lock()
        self._paint_counts: Dict[str, int] = defaultdict(int)
        self._paint_times: Dict[str, List[float]] = defaultdict(list)
        self._total_paints: int = 0

    def record_paint(self, widget_type: str, duration_ms: float):
        with self._lock:
            self._paint_counts[widget_type] += 1
            self._paint_times[widget_type].append(duration_ms)
            self._total_paints += 1

    def get_hot_widgets(self, threshold: float = 5.0) -> List[Dict]:
        with self._lock:
            hot = []
            for wtype, count in self._paint_counts.items():
                if count > threshold:
                    times = self._paint_times.get(wtype, [])
                    avg_time = sum(times) / len(times) if times else 0
                    hot.append({
                        'widget_type': wtype,
                        'paint_count': count,
                        'avg_paint_ms': round(avg_time, 2),
                    })
            return sorted(hot, key=lambda x: -x['paint_count'])

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_paints': self._total_paints,
                'unique_widget_types': len(self._paint_counts),
                'hot_widgets': self.get_hot_widgets(),
                'paint_type_counts': dict(self._paint_counts),
            }


class _WidgetCostTracker:
    """Measures widget construction time to identify expensive components."""

    def __init__(self):
        self._lock = threading.Lock()
        self._costs: deque = deque(maxlen=_MAX_WIDGET_COST_RECORDS)
        self._avg_by_type: Dict[str, List[float]] = defaultdict(list)

    def record_creation(self, widget_type: str, duration_ms: float, screen: str = ""):
        with self._lock:
            self._costs.append({
                'type': widget_type, 'duration_ms': duration_ms,
                'screen': screen, 'ts': time.time()
            })
            self._avg_by_type[widget_type].append(duration_ms)

    def get_expensive_widgets(self, threshold_ms: float = _SLOW_WIDGET_MS) -> List[Dict]:
        with self._lock:
            expensive = []
            for wtype, times in self._avg_by_type.items():
                avg = sum(times) / len(times)
                if avg > threshold_ms:
                    expensive.append({
                        'widget_type': wtype,
                        'avg_creation_ms': round(avg, 1),
                        'instance_count': len(times),
                    })
            return sorted(expensive, key=lambda x: -x['avg_creation_ms'])

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_widgets_tracked': len(self._costs),
                'unique_types': len(self._avg_by_type),
                'expensive_widgets': self.get_expensive_widgets(),
                'avg_creation_by_type': {
                    t: round(sum(v) / len(v), 1)
                    for t, v in self._avg_by_type.items()
                },
            }


class _UIObservabilityAggregator:
    """Aggregates all UI observability components."""

    def __init__(self):
        self.signal_detector = _SignalStormDetector()
        self.repaint_monitor = _RepaintMonitor()
        self.widget_tracker = _WidgetCostTracker()
        self._slow_screens: deque = deque(maxlen=20)
        self._slow_dialogs: deque = deque(maxlen=20)
        self._slow_tables: deque = deque(maxlen=20)

    def record_slow_screen(self, screen: str, duration_ms: float):
        if duration_ms >= _SLOW_SCREEN_MS:
            self._slow_screens.append({
                'screen': screen, 'duration_ms': round(duration_ms, 1),
                'ts': time.time()
            })

    def record_slow_dialog(self, dialog_type: str, duration_ms: float):
        if duration_ms >= _SLOW_DIALOG_MS:
            self._slow_dialogs.append({
                'type': dialog_type, 'duration_ms': round(duration_ms, 1),
                'ts': time.time()
            })

    def record_slow_table(self, table_id: str, duration_ms: float, rows: int):
        if duration_ms >= _SLOW_TABLE_MS:
            self._slow_tables.append({
                'table': table_id, 'duration_ms': round(duration_ms, 1),
                'rows': rows, 'ts': time.time()
            })

    def get_full_report(self) -> Dict[str, Any]:
        return {
            'signal_analysis': self.signal_detector.get_report(),
            'repaint_analysis': self.repaint_monitor.get_report(),
            'widget_creation_costs': self.widget_tracker.get_report(),
            'slow_screens': list(self._slow_screens),
            'slow_dialogs': list(self._slow_dialogs),
            'slow_tables': list(self._slow_tables),
        }


_instance: Optional[_UIObservabilityAggregator] = None
_init_lock = threading.Lock()


def _get_aggregator() -> _UIObservabilityAggregator:
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = _UIObservabilityAggregator()
    return _instance


def record_signal(signal_name: str, source: str = ""):
    try:
        _get_aggregator().signal_detector.record_signal(signal_name, source)
    except Exception:
        pass


def record_paint(widget_type: str, duration_ms: float):
    try:
        _get_aggregator().repaint_monitor.record_paint(widget_type, duration_ms)
    except Exception:
        pass


def record_widget_creation(widget_type: str, duration_ms: float, screen: str = ""):
    try:
        _get_aggregator().widget_tracker.record_creation(widget_type, duration_ms, screen)
    except Exception:
        pass


def record_slow_screen(screen: str, duration_ms: float):
    try:
        _get_aggregator().record_slow_screen(screen, duration_ms)
    except Exception:
        pass


def record_slow_dialog(dialog_type: str, duration_ms: float):
    try:
        _get_aggregator().record_slow_dialog(dialog_type, duration_ms)
    except Exception:
        pass


def record_slow_table(table_id: str, duration_ms: float, rows: int):
    try:
        _get_aggregator().record_slow_table(table_id, duration_ms, rows)
    except Exception:
        pass


def check_signal_storm() -> Optional[Dict]:
    try:
        return _get_aggregator().signal_detector.check_storm()
    except Exception:
        return None


def get_ui_observability_report() -> Dict[str, Any]:
    try:
        return _get_aggregator().get_full_report()
    except Exception:
        return {}


def get_slow_components_report() -> Dict[str, List]:
    try:
        agg = _get_aggregator()
        return {
            'slow_screens': list(agg._slow_screens),
            'slow_dialogs': list(agg._slow_dialogs),
            'slow_tables': list(agg._slow_tables),
        }
    except Exception:
        return {'slow_screens': [], 'slow_dialogs': [], 'slow_tables': []}

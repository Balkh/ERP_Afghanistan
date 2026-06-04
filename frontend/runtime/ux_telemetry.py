"""
Phase UX.5 — Runtime UX Telemetry.

Lightweight, buffered, non-blocking telemetry for user interaction metrics.
All data is kept in-memory with periodic flush to local file.
Zero performance overhead on UI thread.
"""
import time
import json
import os
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QTimer
from utils.logger import get_logger

log = get_logger('telemetry')

_MAX_BUFFER = 500
_FLUSH_INTERVAL_MS = 30000
_TELEMETRY_FILE = "ux_telemetry.jsonl"


class _TelemetryBuffer:
    """Thread-safe, bounded telemetry buffer."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events: deque = deque(maxlen=_MAX_BUFFER)
        self._flush_timer: Optional[QTimer] = None

        self._nav_counts: Dict[str, int] = defaultdict(int)
        self._nav_times: Dict[str, List[float]] = defaultdict(list)
        self._dialog_counts: Dict[str, int] = defaultdict(int)
        self._dialog_times: Dict[str, List[float]] = defaultdict(list)
        self._table_render_counts: int = 0
        self._table_render_times: List[float] = []
        self._form_submits: int = 0
        self._form_cancels: int = 0
        self._exit_points: Dict[str, int] = defaultdict(int)
        self._start_time: float = time.time()

        self._setup_flush()

    def _setup_flush(self):
        """Periodic flush via non-blocking timer."""
        try:
            # F11: Use QApplication.instance() as parent so the timer lifetime
            # is tied to the application and destroyed before the event loop exits.
            from PySide6.QtWidgets import QApplication
            _app = QApplication.instance()
            self._flush_timer = QTimer(_app)
            self._flush_timer.setSingleShot(False)
            self._flush_timer.timeout.connect(self.flush)
            self._flush_timer.start(_FLUSH_INTERVAL_MS)
        except RuntimeError:
            pass

    def record_navigation(self, screen_id: str, duration_ms: float):
        with self._lock:
            self._nav_counts[screen_id] += 1
            self._nav_times[screen_id].append(duration_ms)
            self._events.append({
                'type': 'navigation', 'screen': screen_id,
                'duration_ms': round(duration_ms, 1), 'ts': time.time()
            })

    def record_dialog(self, dialog_type: str, duration_ms: float):
        with self._lock:
            self._dialog_counts[dialog_type] += 1
            self._dialog_times[dialog_type].append(duration_ms)
            self._events.append({
                'type': 'dialog', 'dialog_type': dialog_type,
                'duration_ms': round(duration_ms, 1), 'ts': time.time()
            })

    def record_table_render(self, row_count: int, duration_ms: float):
        with self._lock:
            self._table_render_counts += 1
            self._table_render_times.append(duration_ms)
            self._events.append({
                'type': 'table_render', 'rows': row_count,
                'duration_ms': round(duration_ms, 1), 'ts': time.time()
            })

    def record_form_action(self, action: str):
        with self._lock:
            if action == 'submit':
                self._form_submits += 1
            elif action == 'cancel':
                self._form_cancels += 1
            self._events.append({
                'type': 'form_action', 'action': action, 'ts': time.time()
            })

    def record_exit_point(self, point: str):
        with self._lock:
            self._exit_points[point] += 1
            self._events.append({
                'type': 'exit', 'point': point, 'ts': time.time()
            })

    def flush(self):
        """Flush buffer to local JSONL file."""
        with self._lock:
            if not self._events:
                return
            try:
                filepath = _resolve_telemetry_path()
                with open(filepath, 'a', encoding='utf-8') as f:
                    while self._events:
                        ev = self._events.popleft()
                        f.write(json.dumps(ev, default=str) + '\n')
            except Exception as e:
                log.debug(f"Telemetry flush error: {e}")

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            uptime_s = time.time() - self._start_time
            avg_nav_times = {
                s: round(sum(times) / len(times), 1)
                for s, times in self._nav_times.items()
            } if self._nav_times else {}
            avg_dialog_times = {
                d: round(sum(times) / len(times), 1)
                for d, times in self._dialog_times.items()
            } if self._dialog_times else {}
            avg_table_time = (
                round(sum(self._table_render_times) / len(self._table_render_times), 1)
                if self._table_render_times else 0.0
            )
            total_navs = sum(self._nav_counts.values())
            return {
                'uptime_seconds': round(uptime_s, 1),
                'total_navigations': total_navs,
                'navigation_frequency': {
                    'most_visited': sorted(
                        self._nav_counts.items(), key=lambda x: -x[1]
                    )[:10],
                    'screen_count': len(self._nav_counts),
                },
                'navigation_performance': {
                    'avg_ms_by_screen': avg_nav_times,
                    'overall_avg_ms': (
                        round(sum(
                            t for times in self._nav_times.values() for t in times
                        ) / max(total_navs, 1), 1)
                    ),
                },
                'dialog_metrics': {
                    'total_opened': sum(self._dialog_counts.values()),
                    'avg_ms_by_type': avg_dialog_times,
                    'type_counts': dict(self._dialog_counts),
                },
                'table_render_metrics': {
                    'total_renders': self._table_render_counts,
                    'avg_render_ms': avg_table_time,
                },
                'form_metrics': {
                    'submits': self._form_submits,
                    'cancels': self._form_cancels,
                    'completion_rate': (
                        round(self._form_submits / max(
                            self._form_submits + self._form_cancels, 1
                        ) * 100, 1)
                    ),
                },
                'exit_points': dict(self._exit_points),
            }

    def get_usage_analytics(self) -> Dict[str, Any]:
        with self._lock:
            uptime_h = (time.time() - self._start_time) / 3600
            total_navs = sum(self._nav_counts.values())
            return {
                'session_duration_hours': round(uptime_h, 2),
                'top_screens': [
                    {'screen': s, 'visits': c}
                    for s, c in sorted(
                        self._nav_counts.items(), key=lambda x: -x[1]
                    )[:15]
                ],
                'navigation_intensity': (
                    round(total_navs / max(uptime_h, 0.01), 1)
                ),
                'dialog_usage': dict(self._dialog_counts),
                'form_completion_rate': (
                    round(self._form_submits / max(
                        self._form_submits + self._form_cancels, 1
                    ) * 100, 1)
                ),
                'exit_patterns': dict(self._exit_points),
            }

    def shutdown(self):
        self.flush()
        if self._flush_timer:
            try:
                self._flush_timer.stop()
            except RuntimeError:
                pass


def _resolve_telemetry_path() -> str:
    """Store telemetry next to the app data."""
    base = os.environ.get('ERP_TELEMETRY_DIR', '')
    if base:
        return os.path.join(base, _TELEMETRY_FILE)
    return _TELEMETRY_FILE


_instance: Optional[_TelemetryBuffer] = None
_init_lock = threading.Lock()


def _get_buffer() -> _TelemetryBuffer:
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = _TelemetryBuffer()
    return _instance


def record_navigation(screen_id: str, duration_ms: float):
    try:
        _get_buffer().record_navigation(screen_id, duration_ms)
    except Exception:
        pass


def record_dialog(dialog_type: str, duration_ms: float):
    try:
        _get_buffer().record_dialog(dialog_type, duration_ms)
    except Exception:
        pass


def record_table_render(row_count: int, duration_ms: float):
    try:
        _get_buffer().record_table_render(row_count, duration_ms)
    except Exception:
        pass


def record_form_action(action: str):
    try:
        _get_buffer().record_form_action(action)
    except Exception:
        pass


def record_exit_point(point: str):
    try:
        _get_buffer().record_exit_point(point)
    except Exception:
        pass


def get_telemetry_report() -> Dict[str, Any]:
    try:
        return _get_buffer().get_report()
    except Exception:
        return {}


def get_usage_analytics() -> Dict[str, Any]:
    try:
        return _get_buffer().get_usage_analytics()
    except Exception:
        return {}


def shutdown_telemetry():
    try:
        _get_buffer().shutdown()
    except Exception:
        pass

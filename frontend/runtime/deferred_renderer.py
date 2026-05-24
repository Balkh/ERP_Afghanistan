"""
Phase UX.5 — Deferred Rendering Utility.

Offloads heavy UI work to the next event-loop cycle using QTimer.singleShot(0).
Prevents UI thread blocking during data loading and table rendering.

Usage:
    from runtime.deferred_renderer import defer, defer_until
    defer(my_heavy_function, arg1, arg2)
    defer_until(condition_check, my_callback)
"""
from typing import Callable, Any, Optional
from PySide6.QtCore import QTimer
from utils.logger import get_logger

log = get_logger('perf')


def defer(callback: Callable[..., Any], *args, **kwargs) -> None:
    """Schedule callback for next event-loop cycle (non-blocking).

    Args:
        callback: Function to call
        args, kwargs: Passed to callback on execution
    """
    QTimer.singleShot(0, lambda: callback(*args, **kwargs))


def defer_until(condition: Callable[[], bool], callback: Callable[[], Any],
                interval_ms: int = 50, max_attempts: int = 20) -> None:
    """Defer callback until a condition is met (polling with interval).

    Args:
        condition: Function returning True when ready
        callback: Function to call when condition met
        interval_ms: Polling interval in ms
        max_attempts: Max polls before giving up
    """
    attempts = [0]

    def _check():
        attempts[0] += 1
        if condition():
            callback()
        elif attempts[0] < max_attempts:
            QTimer.singleShot(interval_ms, _check)

    QTimer.singleShot(interval_ms, _check)


class ChunkedRenderer:
    """Renders large datasets in chunks to keep UI responsive.

    Example:
        renderer = ChunkedRenderer(table.set_data, chunk_size=50)
        renderer.start(all_rows)
    """

    def __init__(self, render_fn: Callable, chunk_size: int = 50):
        self._render_fn = render_fn
        self._chunk_size = chunk_size
        self._data: list = []
        self._index = 0
        self._timer: Optional[QTimer] = None

    def start(self, data: list):
        self._data = data
        self._index = 0
        self._render_chunk()

    def _render_chunk(self):
        end = min(self._index + self._chunk_size, len(self._data))
        chunk = self._data[self._index:end]
        if chunk:
            try:
                self._render_fn(chunk)
            except Exception as e:
                log.debug(f"ChunkedRenderer error: {e}")
        self._index = end
        if self._index < len(self._data):
            QTimer.singleShot(0, self._render_chunk)

    def stop(self):
        self._data = []
        self._index = 0

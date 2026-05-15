"""
Lightweight debounce/throttle utility for high-frequency Qt signals.
Prevents redundant handler execution during rapid-fire events (textChanged, etc).

Usage:
    debouncer = Debouncer(callback, delay_ms=300)
    search_input.textChanged.connect(debouncer)
"""

from PySide6.QtCore import QTimer


class Debouncer:
    """Debounces a callable — delays execution until `delay_ms` of inactivity."""

    def __init__(self, callback, delay_ms=300):
        self._callback = callback
        self._delay = delay_ms
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush)

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._timer.stop()
        self._timer.start(self._delay)

    def _flush(self):
        self._callback(*self._args, **self._kwargs)

    def cancel(self):
        self._timer.stop()

    def flush(self):
        """Execute immediately, cancel pending."""
        self._timer.stop()
        self._flush()


class Throttler:
    """Throttles a callable — executes at most once per `interval_ms`."""

    def __init__(self, callback, interval_ms=500):
        self._callback = callback
        self._interval = interval_ms
        self._last_call = 0
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_call)
        self._pending_args = None

    def __call__(self, *args, **kwargs):
        from time import monotonic
        now = int(monotonic() * 1000)
        if now - self._last_call >= self._interval:
            self._last_call = now
            self._callback(*args, **kwargs)
        else:
            self._pending_args = (args, kwargs)
            if not self._timer.isActive():
                remaining = self._interval - (now - self._last_call)
                self._timer.start(remaining)

    def _do_call(self):
        if self._pending_args:
            args, kwargs = self._pending_args
            self._pending_args = None
            from time import monotonic
            self._last_call = int(monotonic() * 1000)
            self._callback(*args, **kwargs)

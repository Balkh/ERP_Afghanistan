import hashlib
import time

from PySide6.QtCore import QObject, Signal, Property, QTimer
from typing import Any, Dict, Optional, List
from enum import Enum, auto
from runtime.timer_registry import register_timer, unregister_owner, record_load, record_skipped_refresh


class ViewState(Enum):
    LOADING = auto()
    READY = auto()
    ERROR = auto()
    EMPTY = auto()
    STALE = auto()


class ObservableProperty:
    def __init__(self, default=None):
        self._default = default


class BaseViewModel(QObject):
    state_changed = Signal(ViewState)
    data_changed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = ViewState.LOADING
        self._data: Dict[str, Any] = {}
        self._error: Optional[str] = None
        self._last_updated: Optional[str] = None

    @Property(ViewState, notify=state_changed)
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if self._state != value:
            self._state = value
            self.state_changed.emit(value)

    def set_data(self, data: Dict[str, Any]):
        self._data = data
        self._state = ViewState.READY
        self.data_changed.emit()

    def set_error(self, message: str):
        self._error = message
        self._state = ViewState.ERROR
        self.error_occurred.emit(message)

    def clear(self):
        self._data = {}
        self._error = None
        self._state = ViewState.EMPTY


class AsyncDataLoader(QObject):
    MIN_INTERVAL_MS = 10000
    _active_endpoints: Dict[str, list] = {}

    data_loaded = Signal(dict)
    load_error = Signal(str)
    loading_started = Signal()
    loading_finished = Signal()

    def __init__(self, api_client, endpoint: str, poll_interval_ms: int = 15000, parent=None, cooldown_ms: int = 1000):
        super().__init__(parent)
        self._api_client = api_client
        self._endpoint = endpoint
        self._poll_interval = max(poll_interval_ms, self.MIN_INTERVAL_MS)
        self._cooldown_ms = cooldown_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.load)
        self._is_loading = False
        self._paused = False
        self._last_load_ms = 0
        self._refresh_count = 0
        self._skipped_count = 0

    def start(self):
        self._paused = False
        if not self._register():
            return
        jitter = self._deterministic_jitter()
        self._timer.start(self._poll_interval)
        register_timer(f"asyncloader_{id(self)}", self._timer)
        QTimer.singleShot(jitter, self.load)

    def _deterministic_jitter(self) -> int:
        h = hashlib.md5(self._endpoint.encode()).hexdigest()
        return (int(h[:4], 16) % min(self._poll_interval, 5000))

    def stop(self):
        self._unregister()
        unregister_owner(f"asyncloader_{id(self)}")
        self._timer.stop()
        self._paused = True

    def _register(self):
        ep = self._endpoint
        existing = self._active_endpoints.get(ep)
        if existing is not None:
            return False
        self._active_endpoints[ep] = [self]
        return True

    def _unregister(self):
        ep = self._endpoint
        existing = self._active_endpoints.get(ep)
        if existing and self in existing:
            existing.remove(self)
            if not existing:
                del self._active_endpoints[ep]

    def pause(self):
        self._paused = True
        self._timer.stop()

    def resume(self):
        if self._paused:
            self._paused = False
            jitter = self._deterministic_jitter()
            self._timer.start(self._poll_interval)
            QTimer.singleShot(jitter, self.load)

    def load(self):
        if self._is_loading or self._paused:
            self._skipped_count += 1
            record_skipped_refresh(self._endpoint)
            return
        now_ms = int(time.monotonic() * 1000)
        if now_ms - self._last_load_ms < self._cooldown_ms:
            self._skipped_count += 1
            record_skipped_refresh(self._endpoint)
            return
        self._is_loading = True
        self._last_load_ms = now_ms
        self._refresh_count += 1
        record_load()
        self.loading_started.emit()
        try:
            data = self._api_client.get(self._endpoint)
            self._is_loading = False
            self.data_loaded.emit(data if isinstance(data, dict) else {})
            self.loading_finished.emit()
        except Exception as e:
            self._is_loading = False
            self.load_error.emit(str(e))
            self.loading_finished.emit()

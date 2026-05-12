from PySide6.QtCore import QObject, Signal, Property, QTimer
from typing import Any, Dict, Optional, List
from enum import Enum, auto


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
    data_loaded = Signal(dict)
    load_error = Signal(str)
    loading_started = Signal()
    loading_finished = Signal()

    def __init__(self, api_client, endpoint: str, poll_interval_ms: int = 5000, parent=None):
        super().__init__(parent)
        self._api_client = api_client
        self._endpoint = endpoint
        self._poll_interval = poll_interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.load)
        self._is_loading = False

    def start(self):
        self.load()
        self._timer.start(self._poll_interval)

    def stop(self):
        self._timer.stop()

    def load(self):
        if self._is_loading:
            return
        self._is_loading = True
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

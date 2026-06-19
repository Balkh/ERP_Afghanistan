"""Background worker QObjects for MainWindow.

Extracted from ui/main_window.py to reduce God Object responsibilities.
Each worker performs a single async task in a QThread and emits a signal
with the result.  Zero coupling to MainWindow internals -- they only
need an ``api_client`` at construction time.
"""

from PySide6.QtCore import QObject, Signal


# ---------------------------------------------------------------------------
# F18 -- Background worker: connection health check
# ---------------------------------------------------------------------------

class ConnectionCheckWorker(QObject):
    """Checks backend reachability in a background thread.

    Emits:
        result(bool) -- True if reachable, False otherwise
        finished()   -- always emitted after run() completes
    """

    result = Signal(bool)
    finished = Signal()

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client

    def run(self):
        try:
            is_reachable = self._api_client.health_check()
        except Exception:
            is_reachable = False
        self.result.emit(is_reachable)
        self.finished.emit()


# ---------------------------------------------------------------------------
# F19 -- Background worker: startup health check
# ---------------------------------------------------------------------------

class StartupHealthWorker(QObject):
    """Performs the startup health check in a background thread.

    Emits:
        result(label, color, status_message) -- UI-ready strings
        finished()                           -- always emitted after run()
    """

    result = Signal(str, str, str)
    finished = Signal()

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client

    def run(self):
        from ui.constants import COLOR_SUCCESS, COLOR_DANGER
        try:
            is_reachable = self._api_client.health_check()
            if not is_reachable:
                self.result.emit("● Offline", COLOR_DANGER, "")
                return
            health_data = self._api_client.get("/api/health/", background=True)
            if isinstance(health_data, dict):
                data = health_data.get('data', health_data)
                db = data.get('database', {})
                db_status = db.get('status', 'unknown')
                if db_status == 'healthy':
                    self.result.emit("● DB OK", COLOR_SUCCESS, "Startup: all systems healthy")
                else:
                    self.result.emit(
                        f"● DB {db_status.upper()}",
                        COLOR_DANGER,
                        f"Startup: DB status {db_status}",
                    )
            else:
                self.result.emit("● Online", COLOR_SUCCESS, "")
        except Exception:
            from ui.constants import COLOR_DANGER as _CD
            self.result.emit("● Error", _CD, "")
        finally:
            self.finished.emit()


# ---------------------------------------------------------------------------
# F22 -- Background worker: company settings
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Generic screen data loader worker
# ---------------------------------------------------------------------------

class ScreenDataWorker(QObject):
    """Run any callable in a background thread.

    Used to move screen load_*() / refresh_data() methods off the UI thread
    so the loading overlay stays responsive and the event loop is not blocked.

    Emits:
        result()  -- always emitted after run() completes (success or failure)
        finished() -- always emitted after run() completes
    """

    result = Signal()
    finished = Signal()

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            self._fn()
        except Exception:
            from utils.logger import get_logger
            get_logger('ui').error(
                f"ScreenDataWorker failure: {self._fn}",
                exc_info=True,
                extra={'extra_fields': {'tags': ['ui', 'background_worker']}},
            )
        self.result.emit()
        self.finished.emit()


# ---------------------------------------------------------------------------
# F22 -- Background worker: company settings
# ---------------------------------------------------------------------------

class CompanySettingsWorker(QObject):
    """Fetches company name from the backend in a background thread.

    Emits:
        result(company_name) -- empty string on failure
        finished()           -- always emitted after run()
    """

    result = Signal(str)
    finished = Signal()

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client

    def run(self):
        try:
            resp = self._api_client.get("/api/companies/config/", background=True)
            if isinstance(resp, dict) and resp.get("success"):
                data = resp.get("data", resp)
                self.result.emit(data.get("company_name", ""))
            else:
                self.result.emit("")
        except Exception:
            self.result.emit("")
        finally:
            self.finished.emit()

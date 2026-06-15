"""Small Qt worker utility for non-blocking API calls from screens."""
from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal


class ApiRequestWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, api_client, method: str, endpoint: str, *, data=None, params=None,
                 headers=None, raw_response: bool = False):
        super().__init__()
        self._api_client = api_client
        self._method = method.upper()
        self._endpoint = endpoint
        self._data = data
        self._params = params
        self._headers = headers
        self._raw_response = raw_response

    def _new_thread_client(self):
        clone = getattr(self._api_client, "clone_for_worker", None)
        if callable(clone):
            return clone()
        from api.client import APIClient
        client = APIClient(base_url=getattr(self._api_client, "base_url", "http://localhost:8000"))
        token = getattr(self._api_client, "_auth_token", None)
        refresh = getattr(self._api_client, "_refresh_token", None)
        if token:
            client.set_auth_token(token)
        if refresh:
            client._refresh_token = refresh
        return client

    def run(self):
        try:
            client = self._new_thread_client()
            result = client._make_request(
                self._method,
                self._endpoint,
                data=self._data,
                params=self._params,
                headers=self._headers,
                raw_response=self._raw_response,
                background=True,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()


class AsyncRequestMixin:
    def _ensure_async_state(self):
        if not hasattr(self, "_active_api_requests"):
            self._active_api_requests = {}

    def _api_client_for_async(self):
        return getattr(self, "api_client", None) or getattr(self, "_api_client", None)

    def run_api_request(
        self,
        key: str,
        method: str,
        endpoint: str,
        *,
        data=None,
        params=None,
        headers=None,
        raw_response: bool = False,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        self._ensure_async_state()
        if key in self._active_api_requests:
            return False
        api_client = self._api_client_for_async()
        if api_client is None:
            if on_error:
                on_error("API client unavailable")
            return False

        worker = ApiRequestWorker(
            api_client,
            method,
            endpoint,
            data=data,
            params=params,
            headers=headers,
            raw_response=raw_response,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        self._active_api_requests[key] = (thread, worker)

        def finish_success(result, request_key=key):
            try:
                if on_success:
                    on_success(result)
            finally:
                self._active_api_requests.pop(request_key, None)

        def finish_error(message, request_key=key):
            try:
                if on_error:
                    on_error(message)
            finally:
                self._active_api_requests.pop(request_key, None)

        thread.started.connect(worker.run)
        worker.finished.connect(finish_success)
        worker.failed.connect(finish_error)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        return True

    def _resume_api_request(self, attr_name: str, callback: Callable[[], None], result: Any):
        setattr(self, attr_name, result)
        callback()

    def _take_api_response(self, attr_name: str):
        result = getattr(self, attr_name)
        delattr(self, attr_name)
        return result

    def cancel_api_requests(self):
        self._ensure_async_state()
        for thread, _worker in list(self._active_api_requests.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
        self._active_api_requests.clear()

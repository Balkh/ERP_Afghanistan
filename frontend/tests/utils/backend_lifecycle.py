"""Backend lifecycle management for integration testing.

Production-grade utilities for managing Django backend lifecycle during frontend tests.
Supports backend discovery, health checking, and cleanup operations.
"""
import os
import sys
import time
import subprocess
import signal
import requests
import pytest
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple


class BackendProcess:
    """Manages a Django backend process for testing."""

    def __init__(
        self,
        backend_path: str,
        host: str = "localhost",
        port: int = 8000,
        timeout: int = 30,
        startup_timeout: int = 15
    ):
        self.backend_path = backend_path
        self.host = host
        self.port = port
        self.timeout = timeout
        self.startup_timeout = startup_timeout
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"

    def start(self) -> bool:
        """Start the Django backend server."""
        if self.is_running():
            return True

        try:
            self.process = subprocess.Popen(
                [sys.executable, "manage.py", "runserver", f"{self.host}:{self.port}", "--noreload"],
                cwd=self.backend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            return self._wait_for_ready()
        except Exception as e:
            print(f"Failed to start backend: {e}")
            return False

    def stop(self) -> None:
        """Stop the Django backend server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            finally:
                self.process = None

    def is_running(self) -> bool:
        """Check if backend is running and responsive."""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/",
                timeout=2
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _wait_for_ready(self) -> bool:
        """Wait for backend to be ready."""
        start_time = time.time()

        while time.time() - start_time < self.startup_timeout:
            if self.is_running():
                return True
            time.sleep(0.5)

        return False

    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get backend health status."""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None


class BackendManager:
    """Manages multiple backend instances for testing."""

    def __init__(self, backend_path: str):
        self.backend_path = backend_path
        self.backends: Dict[str, BackendProcess] = {}

    def get_backend(
        self,
        name: str = "default",
        host: str = "localhost",
        port: int = 8000
    ) -> BackendProcess:
        """Get or create a backend process."""
        key = f"{name}:{host}:{port}"

        if key not in self.backends:
            self.backends[key] = BackendProcess(
                backend_path=self.backend_path,
                host=host,
                port=port
            )

        return self.backends[key]

    def start_all(self) -> Tuple[int, int]:
        """Start all managed backends."""
        started = 0
        failed = 0

        for backend in self.backends.values():
            if backend.start():
                started += 1
            else:
                failed += 1

        return started, failed

    def stop_all(self) -> None:
        """Stop all managed backends."""
        for backend in self.backends.values():
            backend.stop()


@contextmanager
def backend_session(
    backend_path: str,
    host: str = "localhost",
    port: int = 8000,
    ensure_running: bool = True
):
    """Context manager for backend session.

    Usage:
        with backend_session(backend_path) as backend:
            # Test against running backend
            response = requests.get(backend.base_url + "/api/health/")
    """
    manager = BackendManager(backend_path)
    backend = manager.get_backend(port=port, host=host)

    if ensure_running:
        if not backend.start():
            pytest.skip(f"Could not start backend at {backend.base_url}")

    try:
        yield backend
    finally:
        pass


class BackendHealthChecker:
    """Comprehensive health checking for backend."""

    ENDPOINTS = {
        "health": "/api/health/",
        "auth": "/api/auth/",
        "inventory": "/api/inventory/products/",
        "sales": "/api/sales/invoices/",
        "accounting": "/api/accounting/accounts/",
    }

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_all_endpoints(self) -> Dict[str, Any]:
        """Check all critical endpoints."""
        results = {
            "base_url": self.base_url,
            "overall_healthy": False,
            "endpoints": {},
            "response_times": {}
        }

        overall_healthy = True

        for name, endpoint in self.ENDPOINTS.items():
            start_time = time.time()

            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    timeout=self.timeout
                )
                elapsed = time.time() - start_time

                results["endpoints"][name] = {
                    "status_code": response.status_code,
                    "reachable": True,
                    "error": None
                }
                results["response_times"][name] = round(elapsed * 1000, 2)

                if response.status_code >= 400:
                    overall_healthy = False

            except requests.RequestException as e:
                elapsed = time.time() - start_time

                results["endpoints"][name] = {
                    "status_code": None,
                    "reachable": False,
                    "error": str(e)
                }
                results["response_times"][name] = round(elapsed * 1000, 2)
                overall_healthy = False

        results["overall_healthy"] = overall_healthy
        return results

    def is_ready(self) -> bool:
        """Check if backend is ready for integration tests."""
        try:
            response = requests.get(
                f"{self.base_url}/api/health/",
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def wait_for_ready(self, max_wait: int = 30) -> bool:
        """Wait for backend to become ready."""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if self.is_ready():
                return True
            time.sleep(0.5)

        return False


@pytest.fixture(scope="session")
def backend_path() -> str:
    """Get the backend path for tests."""
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..", "..", "backend"
    ))


@pytest.fixture(scope="session")
def backend_health_checker() -> BackendHealthChecker:
    """Create a backend health checker."""
    return BackendHealthChecker()


@pytest.fixture(scope="function")
def running_backend(backend_path) -> Optional[BackendProcess]:
    """Fixture that provides a running backend or skips test."""
    manager = BackendManager(backend_path)
    backend = manager.get_backend()

    if not backend.is_running():
        if not backend.start():
            pytest.skip("Backend not running and could not be started")

    yield backend


@pytest.fixture(scope="session")
def backend_manager(backend_path) -> BackendManager:
    """Session-scoped backend manager."""
    return BackendManager(backend_path)
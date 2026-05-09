"""Reusable integration utilities for frontend/backend testing.

Production-grade utilities for:
- API client wrappers
- Response handling
- Test data factories
- Performance measurement
- Integration test patterns
"""
import os
import time
import uuid
import pytest
import requests
from typing import Optional, Dict, Any, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager


class TestEnvironment(Enum):
    """Test environment types."""
    LIVE = "live"
    MOCK = "mock"
    HYBRID = "hybrid"


@dataclass
class APIResponse:
    """Standardized API response wrapper."""
    status_code: int
    data: Any
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx)."""
        return 500 <= self.status_code < 600


class IntegrationTestClient:
    """Production-grade integration test client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 10,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self._auth_token: Optional[str] = None

    def set_auth(self, token: str) -> None:
        """Set authentication token."""
        self._auth_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_auth(self) -> None:
        """Clear authentication token."""
        self._auth_token = None
        self.session.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """Make HTTP request with timing and error handling."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=kwargs.get("timeout", self.timeout),
                **kwargs
            )

            elapsed_ms = (time.time() - start_time) * 1000

            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            return APIResponse(
                status_code=response.status_code,
                data=response_data,
                headers=dict(response.headers),
                elapsed_ms=elapsed_ms
            )

        except requests.RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return APIResponse(
                status_code=0,
                data=None,
                elapsed_ms=elapsed_ms,
                error=str(e)
            )

    def get(self, endpoint: str, **kwargs) -> APIResponse:
        """Make GET request."""
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """Make POST request."""
        return self.request("POST", endpoint, data=data, **kwargs)

    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """Make PUT request."""
        return self.request("PUT", endpoint, data=data, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """Make DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_product(name: Optional[str] = None) -> Dict[str, Any]:
        """Create product test data."""
        return {
            "name": name or f"Test Product {uuid.uuid4().hex[:8]}",
            "generic_name": "Test Generic",
            "brand_name": "Test Brand",
            "is_active": True
        }

    @staticmethod
    def create_category(name: Optional[str] = None) -> Dict[str, Any]:
        """Create category test data."""
        return {
            "name": name or f"Test Category {uuid.uuid4().hex[:8]}",
            "description": "Test category"
        }

    @staticmethod
    def create_warehouse(name: Optional[str] = None) -> Dict[str, Any]:
        """Create warehouse test data."""
        return {
            "name": name or f"Test Warehouse {uuid.uuid4().hex[:8]}",
            "address": "Test Address",
            "is_active": True
        }

    @staticmethod
    def create_customer(name: Optional[str] = None) -> Dict[str, Any]:
        """Create customer test data."""
        return {
            "name": name or f"Test Customer {uuid.uuid4().hex[:8]}",
            "phone": "1234567890",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "is_active": True
        }

    @staticmethod
    def create_supplier(name: Optional[str] = None) -> Dict[str, Any]:
        """Create supplier test data."""
        return {
            "name": name or f"Test Supplier {uuid.uuid4().hex[:8]}",
            "phone": "1234567890",
            "email": f"supplier_{uuid.uuid4().hex[:8]}@example.com",
            "is_active": True
        }

    @staticmethod
    def create_invoice(customer_id: int) -> Dict[str, Any]:
        """Create invoice test data."""
        return {
            "customer_id": customer_id,
            "invoice_number": f"INV-{int(time.time())}-{uuid.uuid4().hex[:4]}",
            "items": [],
            "total_amount": 0
        }

    @staticmethod
    def create_account(code: Optional[str] = None) -> Dict[str, Any]:
        """Create account test data."""
        return {
            "code": code or f"{9000 + int(time.time() % 1000)}",
            "name": f"Test Account {uuid.uuid4().hex[:8]}",
            "account_type": "ASSET",
            "balance_type": "DEBIT"
        }


class PerformanceMonitor:
    """Monitor API performance during tests."""

    def __init__(self):
        self._measurements: List[Dict[str, Any]] = []

    def record(self, endpoint: str, method: str, elapsed_ms: float, status_code: int) -> None:
        """Record a performance measurement."""
        self._measurements.append({
            "endpoint": endpoint,
            "method": method,
            "elapsed_ms": elapsed_ms,
            "status_code": status_code,
            "timestamp": time.time()
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._measurements:
            return {"count": 0}

        times = [m["elapsed_ms"] for m in self._measurements]
        status_codes = [m["status_code"] for m in self._measurements]

        return {
            "count": len(self._measurements),
            "avg_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "success_rate": sum(1 for s in status_codes if 200 <= s < 300) / len(status_codes)
        }

    def clear(self) -> None:
        """Clear all measurements."""
        self._measurements.clear()


class RetryPolicy:
    """Configurable retry policy for API requests."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        exponential: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        if self.exponential:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay

        return min(delay, self.max_delay)


@dataclass
class IntegrationTestResult:
    """Result of an integration test."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class IntegrationTestSuite:
    """Manages integration test execution."""

    def __init__(self, client: IntegrationTestClient):
        self.client = client
        self.results: List[IntegrationTestResult] = []
        self.performance = PerformanceMonitor()

    def run_test(
        self,
        name: str,
        test_func: Callable[[IntegrationTestClient], bool]
    ) -> IntegrationTestResult:
        """Run a single integration test."""
        start_time = time.time()

        try:
            passed = test_func(self.client)
            duration_ms = (time.time() - start_time) * 1000

            result = IntegrationTestResult(
                name=name,
                passed=passed,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = IntegrationTestResult(
                name=name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e)
            )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get test suite summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "performance": self.performance.get_stats(),
            "duration_ms": sum(r.duration_ms for r in self.results)
        }


@contextmanager
def measure_performance(monitor: PerformanceMonitor, endpoint: str, method: str):
    """Context manager for measuring API performance."""
    start_time = time.time()
    status_code = 0

    try:
        yield
        status_code = 200
    except Exception:
        status_code = 500
        raise
    finally:
        elapsed_ms = (time.time() - start_time) * 1000
        monitor.record(endpoint, method, elapsed_ms, status_code)


@pytest.fixture
def integration_client() -> IntegrationTestClient:
    """Provide integration test client."""
    base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    return IntegrationTestClient(base_url=base_url)


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Provide test data factory."""
    return TestDataFactory()


@pytest.fixture
def performance_monitor() -> PerformanceMonitor:
    """Provide performance monitor."""
    return PerformanceMonitor()


@pytest.fixture
def integration_suite(integration_client) -> IntegrationTestSuite:
    """Provide integration test suite."""
    return IntegrationTestSuite(integration_client)


def requires_backend(test_func):
    """Decorator to skip test if backend is not available."""
    def wrapper(*args, **kwargs):
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        try:
            response = requests.get(f"{base_url}/api/health/", timeout=2)
            if response.status_code != 200:
                pytest.skip("Backend not healthy")
        except requests.RequestException:
            pytest.skip("Backend not available")

        return test_func(*args, **kwargs)

    return wrapper
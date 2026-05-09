"""API integration fixtures with proper isolation.

Production-grade fixtures for frontend/backend integration testing.
Supports authenticated requests, test isolation, and proper resource cleanup.
"""
import os
import time
import requests
import pytest
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class APIClient:
    """Production API client for integration tests."""

    DEFAULT_TIMEOUT = 10
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 0.5

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self._auth_token: Optional[str] = None

    def set_auth(self, token: str) -> None:
        """Set authentication token."""
        self._auth_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_auth(self) -> None:
        """Clear authentication token."""
        self._auth_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        allow_redirects: bool = True
    ) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        request_headers = self.session.headers.copy()

        if headers:
            request_headers.update(headers)

        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                    allow_redirects=allow_redirects
                )
                return response

            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == self.RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(self.RETRY_DELAY)

        raise requests.RequestException("Max retries exceeded")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> requests.Response:
        """Make GET request."""
        return self._request("GET", endpoint, params=params, headers=headers)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> requests.Response:
        """Make POST request."""
        return self._request("POST", endpoint, data=data, headers=headers)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> requests.Response:
        """Make PUT request."""
        return self._request("PUT", endpoint, data=data, headers=headers)

    def patch(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> requests.Response:
        """Make PATCH request."""
        return self._request("PATCH", endpoint, data=data, headers=headers)

    def delete(
        self,
        endpoint: str,
        headers: Optional[Dict] = None
    ) -> requests.Response:
        """Make DELETE request."""
        return self._request("DELETE", endpoint, headers=headers)


class AuthenticatedAPIClient(APIClient):
    """API client with authentication capabilities."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = None):
        super().__init__(base_url, timeout)
        self._credentials: Optional[Dict[str, str]] = None

    def login(self, username: str, password: str) -> bool:
        """Login and store authentication token."""
        try:
            response = self.post("/api/auth/login/", {
                "username": username,
                "password": password
            })

            if response.status_code == 200:
                data = response.json()
                token = data.get("token") or data.get("access")
                if token:
                    self.set_auth(token)
                    self._credentials = {"username": username, "password": password}
                    return True

            return False

        except requests.RequestException:
            return False

    def logout(self) -> None:
        """Logout and clear authentication."""
        try:
            self.post("/api/auth/logout/")
        except requests.RequestException:
            pass
        finally:
            self.clear_auth()
            self._credentials = None

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._auth_token is not None


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Get API base URL from environment or default."""
    return os.environ.get("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="function")
def api_client(api_base_url: str) -> APIClient:
    """Create a fresh API client for each test."""
    client = APIClient(base_url=api_base_url)
    yield client


@pytest.fixture(scope="function")
def authenticated_client(api_base_url: str) -> AuthenticatedAPIClient:
    """Create an authenticated API client.

    Note: Requires backend to have test user configured.
    """
    client = AuthenticatedAPIClient(base_url=api_base_url)

    username = os.environ.get("TEST_USERNAME", "admin")
    password = os.environ.get("TEST_PASSWORD", "admin123")

    if client.login(username, password):
        yield client
        client.logout()
    else:
        pytest.skip(f"Could not authenticate with {username}")


@pytest.fixture(scope="session")
def api_client_shared(api_base_url: str) -> APIClient:
    """Create a shared API client for session-scoped tests."""
    return APIClient(base_url=api_base_url)


class EndpointRegistry:
    """Registry of API endpoints for testing."""

    INVENTORY = {
        "products": "/api/inventory/products/",
        "categories": "/api/inventory/categories/",
        "warehouses": "/api/inventory/warehouses/",
        "batches": "/api/inventory/batches/",
        "units": "/api/inventory/units/",
    }

    SALES = {
        "invoices": "/api/sales/invoices/",
        "customers": "/api/sales/customers/",
    }

    PURCHASES = {
        "invoices": "/api/purchases/invoices/",
        "suppliers": "/api/purchases/suppliers/",
    }

    ACCOUNTING = {
        "accounts": "/api/accounting/accounts/",
        "journal": "/api/accounting/journal/",
        "trial_balance": "/api/accounting/trial-balance/",
        "profit_loss": "/api/accounting/profit-loss/",
        "balance_sheet": "/api/accounting/balance-sheet/",
    }

    HR = {
        "employees": "/api/hr/employees/",
        "departments": "/api/hr/departments/",
        "positions": "/api/hr/positions/",
        "attendance": "/api/hr/attendance/",
    }

    PAYROLL = {
        "payrolls": "/api/payroll/payrolls/",
        "salaries": "/api/payroll/salaries/",
    }

    ALL = {}
    for group in [INVENTORY, SALES, PURCHASES, ACCOUNTING, HR, PAYROLL]:
        ALL.update(group)

    @classmethod
    def get_endpoint(cls, name: str) -> Optional[str]:
        """Get endpoint URL by name."""
        return cls.ALL.get(name)

    @classmethod
    def get_all_endpoints(cls) -> List[str]:
        """Get all registered endpoints."""
        return list(cls.ALL.values())


@pytest.fixture
def endpoint_registry() -> EndpointRegistry:
    """Fixture providing endpoint registry."""
    return EndpointRegistry


@pytest.fixture
def skip_if_no_backend(api_base_url: str) -> None:
    """Skip test if backend is not available."""
    try:
        response = requests.get(
            f"{api_base_url}/api/health/",
            timeout=2
        )
        if response.status_code != 200:
            pytest.skip("Backend not healthy")
    except requests.RequestException:
        pytest.skip("Backend not available")


@pytest.fixture
def create_test_data_helper(api_client: APIClient):
    """Helper fixture for creating test data via API."""
    created_resources: List[Dict[str, Any]] = []

    def create(category: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create test data and track for cleanup."""
        endpoint = EndpointRegistry.ALL.get(category)
        if not endpoint:
            return None

        try:
            response = api_client.post(endpoint, data)
            if response.status_code in [200, 201]:
                result = response.json()
                created_resources.append({
                    "category": category,
                    "id": result.get("id"),
                    "endpoint": endpoint
                })
                return result
        except requests.RequestException:
            pass

        return None

    yield create

    for resource in reversed(created_resources):
        try:
            api_client.delete(f"{resource['endpoint']}{resource['id']}/")
        except requests.RequestException:
            pass


@pytest.fixture(scope="function")
def isolated_api_client(api_base_url: str) -> APIClient:
    """API client with transaction isolation awareness."""
    client = APIClient(base_url=api_base_url)

    client._transaction_id = f"test_{int(time.time() * 1000)}"

    yield client

    client.clear_auth()
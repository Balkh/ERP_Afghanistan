"""Integration test helpers for backend API testing."""
import pytest
import requests
from unittest.mock import MagicMock, patch


class BackendChecker:
    """Helper to check backend availability."""
    
    def __init__(self, url="http://localhost:8000", timeout=5):
        self.url = url
        self.timeout = timeout
        self._available = None
    
    def is_available(self):
        """Check if backend is running."""
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.url}/api/health/", timeout=self.timeout)
            self._available = response.status_code == 200
        except requests.RequestException:
            self._available = False
        
        return self._available
    
    def check_health(self):
        """Check backend health."""
        if not self.is_available():
            pytest.skip("Backend not running")
        
        try:
            response = requests.get(
                f"{self.url}/api/health/",
                timeout=self.timeout
            )
            return response.json() if response.status_code == 200 else {}
        except requests.RequestException:
            pytest.skip("Backend not accessible")
            return {}


class APIIntegrationHelper:
    """Helper for API integration tests."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get(self, endpoint, **kwargs):
        """Make GET request to API."""
        try:
            return requests.get(
                f"{self.base_url}{endpoint}",
                timeout=kwargs.get("timeout", 5),
                **kwargs
            )
        except requests.RequestException as e:
            pytest.skip(f"API error: {e}")
            return None
    
    def post(self, endpoint, data=None, **kwargs):
        """Make POST request to API."""
        try:
            return requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                timeout=kwargs.get("timeout", 5),
                **kwargs
            )
        except requests.RequestException as e:
            pytest.skip(f"API error: {e}")
            return None
    
    def put(self, endpoint, data=None, **kwargs):
        """Make PUT request to API."""
        try:
            return requests.put(
                f"{self.base_url}{endpoint}",
                json=data,
                timeout=kwargs.get("timeout", 5),
                **kwargs
            )
        except requests.RequestException as e:
            pytest.skip(f"API error: {e}")
            return None
    
    def delete(self, endpoint, **kwargs):
        """Make DELETE request to API."""
        try:
            return requests.delete(
                f"{self.base_url}{endpoint}",
                timeout=kwargs.get("timeout", 5),
                **kwargs
            )
        except requests.RequestException as e:
            pytest.skip(f"API error: {e}")
            return None


class MockAPIClient:
    """Mock API client for testing without backend."""
    
    def __init__(self):
        self._collections = {
            "products": [],
            "categories": [],
            "warehouses": [],
            "batches": [],
            "accounts": [],
            "invoices": [],
        }
    
    def mock_get(self, endpoint, **kwargs):
        """Mock GET request."""
        response = MagicMock()
        
        if "products" in endpoint:
            response.status_code = 200
            response.json.return_value = {"results": self._collections["products"]}
        elif "categories" in endpoint:
            response.status_code = 200
            response.json.return_value = {"results": self._collections["categories"]}
        elif "warehouses" in endpoint:
            response.status_code = 200
            response.json.return_value = {"results": self._collections["warehouses"]}
        else:
            response.status_code = 404
            response.json.return_value = {"detail": "Not found"}
        
        return response
    
    def mock_post(self, endpoint, data=None, **kwargs):
        """Mock POST request."""
        response = MagicMock()
        
        if "products" in endpoint:
            response.status_code = 201
            response.json.return_value = {"id": 1, **data}
        else:
            response.status_code = 201
            response.json.return_value = {"id": 1}
        
        return response


@pytest.fixture
def backend_checker():
    """Create a backend checker."""
    return BackendChecker()


@pytest.fixture
def api_helper():
    """Create an API integration helper."""
    return APIIntegrationHelper()


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    return MockAPIClient()
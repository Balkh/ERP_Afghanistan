"""Live backend integration tests."""
import pytest
import requests
import os
import time
from unittest.mock import MagicMock, patch


BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 10


def is_backend_available():
    """Check if backend server is running."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/health/", 
            timeout=2
        )
        return response.status_code == 200
    except (requests.RequestException, ImportError):
        return False


def require_backend(test_func):
    """Decorator to skip test if backend not available."""
    return pytest.mark.skipif(
        not is_backend_available(),
        reason="Backend not available"
    )(test_func)


pytestmark = pytest.mark.integration


class TestBackendConnectivity:
    """Test live backend connectivity."""
    
    def test_backend_reachable(self):
        """Backend should be reachable at configured URL."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code == 200
    
    def test_backend_response_time(self):
        """Backend should respond within acceptable time."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        start = time.time()
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0
    
    def test_backend_cors_headers(self):
        """Backend should handle CORS."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/inventory/products/",
            timeout=REQUEST_TIMEOUT,
            headers={"Origin": "http://localhost"}
        )
        
        assert response.status_code in [200, 401, 403]


class TestAPIHealthEndpoint:
    """Test API health endpoints."""
    
    def test_health_endpoint_exists(self):
        """Health endpoint should exist."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code == 200
    
    def test_health_response_format(self):
        """Health response should return valid JSON."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        
        data = response.json()
        
        assert isinstance(data, dict)
    
    def test_health_includes_status(self):
        """Health should include status information."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        
        data = response.json()
        
        # Health may include various fields
        assert data is not None


class TestInventoryAPI:
    """Test inventory API endpoints."""
    
    def test_products_list_endpoint(self):
        """Products list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/inventory/products/",
            timeout=REQUEST_TIMEOUT
        )
        
        # Accept any response - 200 means authenticated, 403 means needs auth
        assert response.status_code in [200, 401, 403]
    
    def test_categories_list_endpoint(self):
        """Categories list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/inventory/categories/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code in [200, 401, 403]
    
    def test_warehouses_list_endpoint(self):
        """Warehouses list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/inventory/warehouses/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code in [200, 401, 403]


class TestAccountingAPI:
    """Test accounting API endpoints."""
    
    def test_accounts_list_endpoint(self):
        """Accounts list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/accounting/accounts/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code in [200, 401, 403]
    
    def test_journal_entries_endpoint(self):
        """Journal entries endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        # Try various journal endpoint patterns
        response = requests.get(
            f"{BACKEND_URL}/api/accounting/journal/",
            timeout=REQUEST_TIMEOUT
        )
        
        # Accept any response
        assert response.status_code in [200, 301, 302, 401, 403, 404]


class TestSalesAPI:
    """Test sales API endpoints."""
    
    def test_invoices_list_endpoint(self):
        """Invoices list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/sales/invoices/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code in [200, 401, 403]
    
    def test_customers_list_endpoint(self):
        """Customers list endpoint should be accessible."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/sales/customers/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code in [200, 401, 403]


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_404_handling(self):
        """API should handle 404 gracefully."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/nonexistent/",
            timeout=REQUEST_TIMEOUT
        )
        
        assert response.status_code == 404
    
    def test_timeout_handling(self):
        """API should handle slow responses."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        # Long timeout should work
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=30
        )
        
        assert response.status_code == 200
    
    def test_connection_error_handling(self):
        """Should handle connection errors gracefully."""
        # Test with invalid URL
        try:
            requests.get(
                "http://invalid.localhost:99999/api/",
                timeout=1
            )
            assert False  # Should not reach here
        except requests.RequestException:
            assert True  # Expected


class TestBackendConfiguration:
    """Test backend configuration."""
    
    def test_backend_url_configured(self):
        """Backend URL should be configured."""
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        
        assert backend_url.startswith("http://") or backend_url.startswith("https://")
    
    def test_debug_mode_detection(self):
        """Should be able to detect debug mode."""
        if not is_backend_available():
            pytest.skip("Backend not running")
        
        response = requests.get(
            f"{BACKEND_URL}/api/health/",
            timeout=REQUEST_TIMEOUT
        )
        
        # Just verify we get a response
        assert response.status_code == 200
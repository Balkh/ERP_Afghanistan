"""API client unit tests.

Test API client in isolation without full window.
"""
import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.qt


class TestAPIClientBasics:
    """Test basic API client functionality."""

    @pytest.fixture
    def api_client(self):
        """Create API client instance."""
        from api.client import APIClient
        return APIClient(base_url="http://test.example.com")

    def test_client_has_base_url(self, api_client):
        """Client should have base URL set."""
        assert api_client.base_url == "http://test.example.com"

    def test_client_has_session(self, api_client):
        """Client should have a requests session."""
        assert api_client.session is not None

    def test_client_default_headers(self, api_client):
        """Client should have default headers."""
        assert "Content-Type" in api_client.session.headers
        assert "Accept" in api_client.session.headers

    def test_set_auth_token(self, api_client):
        """Should set authorization token."""
        api_client.set_auth_token("test_token_123")
        assert "Authorization" in api_client.session.headers
        assert api_client.session.headers["Authorization"] == "Bearer test_token_123"

    def test_clear_auth_token(self, api_client):
        """Should clear authorization token."""
        api_client.set_auth_token("test_token_123")
        api_client.clear_auth_token()
        assert "Authorization" not in api_client.session.headers


class TestAPIClientMethods:
    """Test API client HTTP methods."""

    @pytest.fixture
    def api_client(self):
        """Create API client instance."""
        from api.client import APIClient
        return APIClient(base_url="http://test.example.com")

    def test_get_method_exists(self, api_client):
        """Client should have get method."""
        assert hasattr(api_client, 'get')
        assert callable(api_client.get)

    def test_post_method_exists(self, api_client):
        """Client should have post method."""
        assert hasattr(api_client, 'post')
        assert callable(api_client.post)

    def test_put_method_exists(self, api_client):
        """Client should have put method."""
        assert hasattr(api_client, 'put')
        assert callable(api_client.put)

    def test_delete_method_exists(self, api_client):
        """Client should have delete method."""
        assert hasattr(api_client, 'delete')
        assert callable(api_client.delete)


class TestAPIClientSignals:
    """Test API client Qt signals."""

    @pytest.fixture
    def api_client(self):
        """Create API client instance."""
        from api.client import APIClient
        return APIClient()

    def test_has_request_started_signal(self, api_client):
        """Client should have request_started signal."""
        assert hasattr(api_client, 'request_started')

    def test_has_request_finished_signal(self, api_client):
        """Client should have request_finished signal."""
        assert hasattr(api_client, 'request_finished')

    def test_has_request_error_signal(self, api_client):
        """Client should have request_error signal."""
        assert hasattr(api_client, 'request_error')

    def test_has_response_received_signal(self, api_client):
        """Client should have response_received signal."""
        assert hasattr(api_client, 'response_received')


class TestAPIClientEndpoint:
    """Test API client endpoint construction."""

    @pytest.fixture
    def api_client(self):
        """Create API client instance."""
        from api.client import APIClient
        return APIClient(base_url="http://localhost:8000")

    def test_builds_products_endpoint(self, api_client):
        """Should construct products endpoint URL."""
        endpoint = "/api/inventory/products/"
        url = f"{api_client.base_url}{endpoint}"
        assert url == "http://localhost:8000/api/inventory/products/"

    def test_builds_categories_endpoint(self, api_client):
        """Should construct categories endpoint URL."""
        endpoint = "/api/inventory/categories/"
        url = f"{api_client.base_url}{endpoint}"
        assert url == "http://localhost:8000/api/inventory/categories/"

    def test_builds_accounting_endpoint(self, api_client):
        """Should construct accounting endpoint URL."""
        endpoint = "/api/accounting/accounts/"
        url = f"{api_client.base_url}{endpoint}"
        assert url == "http://localhost:8000/api/accounting/accounts/"
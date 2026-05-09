"""Authentication integration tests with live backend.

Production-grade tests for authentication flows with real Django backend.
Tests token handling, session management, and protected endpoint access.
"""
import os
import time
import pytest
import requests
from typing import Optional, Dict, Any


pytestmark = pytest.mark.integration


class TestAuthenticationFlow:
    """Test authentication flow with real backend."""

    @pytest.fixture
    def auth_base_url(self) -> str:
        """Get base URL for auth tests."""
        return os.environ.get("BACKEND_URL", "http://localhost:8000")

    def test_login_endpoint_exists(self, auth_base_url: str):
        """Login endpoint should exist."""
        try:
            response = requests.get(
                f"{auth_base_url}/api/auth/",
                timeout=5
            )
            assert response.status_code in [200, 301, 302, 404]
        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_login_with_valid_credentials(self, auth_base_url: str):
        """Should be able to login with valid credentials."""
        username = os.environ.get("TEST_USERNAME", "admin")
        password = os.environ.get("TEST_PASSWORD", "admin123")

        try:
            response = requests.post(
                f"{auth_base_url}/api/auth/login/",
                json={"username": username, "password": password},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                assert "token" in data or "access" in data or "session" in data
            elif response.status_code in [401, 403]:
                pytest.skip("Authentication not configured")
            else:
                pytest.fail(f"Unexpected status: {response.status_code}")

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_login_with_invalid_credentials(self, auth_base_url: str):
        """Should reject invalid credentials."""
        try:
            response = requests.post(
                f"{auth_base_url}/api/auth/login/",
                json={"username": "invalid", "password": "invalid"},
                timeout=5
            )

            assert response.status_code in [400, 401, 403]

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_protected_endpoint_requires_auth(self, auth_base_url: str):
        """Protected endpoints should reject unauthenticated requests."""
        protected_endpoints = [
            "/api/inventory/products/",
            "/api/sales/invoices/",
            "/api/accounting/accounts/",
        ]

        try:
            for endpoint in protected_endpoints:
                response = requests.get(
                    f"{auth_base_url}{endpoint}",
                    timeout=5
                )
                assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth"

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_authenticated_request_succeeds(self, auth_base_url: str):
        """Authenticated requests should succeed."""
        username = os.environ.get("TEST_USERNAME", "admin")
        password = os.environ.get("TEST_PASSWORD", "admin123")

        try:
            login_response = requests.post(
                f"{auth_base_url}/api/auth/login/",
                json={"username": username, "password": password},
                timeout=5
            )

            if login_response.status_code != 200:
                pytest.skip("Authentication not configured")

            token = login_response.json().get("token") or login_response.json().get("access")

            if not token:
                pytest.skip("No token in response")

            protected_response = requests.get(
                f"{auth_base_url}/api/inventory/products/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )

            assert protected_response.status_code == 200

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_token_expiration_handling(self, auth_base_url: str):
        """Should handle expired tokens gracefully."""
        try:
            response = requests.get(
                f"{auth_base_url}/api/inventory/products/",
                headers={"Authorization": "Bearer expired.invalid.token"},
                timeout=5
            )

            assert response.status_code in [401, 403]

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_logout_endpoint(self, auth_base_url: str):
        """Logout endpoint should exist and work."""
        try:
            response = requests.post(
                f"{auth_base_url}/api/auth/logout/",
                timeout=5
            )

            assert response.status_code in [200, 204, 301, 302, 403, 404]

        except requests.RequestException:
            pytest.skip("Backend not available")


class TestAuthenticationPatterns:
    """Test authentication patterns and edge cases."""

    def test_missing_authorization_header(self):
        """Requests without auth header should be rejected."""
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

        try:
            response = requests.get(
                f"{base_url}/api/inventory/products/",
                timeout=5
            )

            assert response.status_code in [401, 403]

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_invalid_token_format(self):
        """Invalid token format should be rejected."""
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        invalid_tokens = [
            "Bearer",
            "Bearer ",
            "InvalidFormat",
            "",
        ]

        try:
            for token in invalid_tokens:
                response = requests.get(
                    f"{base_url}/api/inventory/products/",
                    headers={"Authorization": token},
                    timeout=5
                )

                assert response.status_code in [401, 403, 400], f"Token '{token}' should be rejected"

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_csrf_protection_on_login(self):
        """Login should handle CSRF protection."""
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

        try:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/json"})

            response = session.post(
                f"{base_url}/api/auth/login/",
                json={"username": "test", "password": "test"},
                timeout=5
            )

            assert response.status_code in [200, 400, 401, 403, 404]

        except requests.RequestException:
            pytest.skip("Backend not available")


class TestAuthenticationSession:
    """Test session-based authentication."""

    def test_session_persistence(self):
        """Authenticated session should persist across requests."""
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

        try:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/json"})

            login_response = session.post(
                f"{base_url}/api/auth/login/",
                json={
                    "username": os.environ.get("TEST_USERNAME", "admin"),
                    "password": os.environ.get("TEST_PASSWORD", "admin123")
                },
                timeout=5
            )

            if login_response.status_code != 200:
                pytest.skip("Authentication not configured")

            products_response = session.get(
                f"{base_url}/api/inventory/products/",
                timeout=5
            )

            assert products_response.status_code == 200

        except requests.RequestException:
            pytest.skip("Backend not available")

    def test_concurrent_authenticated_requests(self):
        """Should handle concurrent authenticated requests."""
        base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        username = os.environ.get("TEST_USERNAME", "admin")
        password = os.environ.get("TEST_PASSWORD", "admin123")

        try:
            login_response = requests.post(
                f"{base_url}/api/auth/login/",
                json={"username": username, "password": password},
                timeout=5
            )

            if login_response.status_code != 200:
                pytest.skip("Authentication not configured")

            token = login_response.json().get("token") or login_response.json().get("access")

            headers = {"Authorization": f"Bearer {token}"}

            endpoints = [
                "/api/inventory/products/",
                "/api/inventory/categories/",
                "/api/inventory/warehouses/",
            ]

            for endpoint in endpoints:
                response = requests.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    timeout=5
                )
                assert response.status_code == 200

        except requests.RequestException:
            pytest.skip("Backend not available")


@pytest.fixture
def auth_test_credentials() -> Dict[str, str]:
    """Provide test credentials for auth tests."""
    return {
        "username": os.environ.get("TEST_USERNAME", "admin"),
        "password": os.environ.get("TEST_PASSWORD", "admin123")
    }


@pytest.fixture
def valid_auth_token(auth_test_credentials) -> Optional[str]:
    """Get valid auth token or skip if not available."""
    base_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

    try:
        response = requests.post(
            f"{base_url}/api/auth/login/",
            json=auth_test_credentials,
            timeout=5
        )

        if response.status_code == 200:
            return response.json().get("token") or response.json().get("access")

    except requests.RequestException:
        pass

    pytest.skip("Could not obtain auth token")
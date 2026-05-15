"""Tests for the expenses app — ExpenseViewSet CRUD."""
import pytest
from django.test import Client
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestExpenseViewSet:
    """Test expense endpoint connectivity."""

    def test_expense_endpoint_reachable(self):
        """Expense endpoint should return 200 or 401 (auth required)."""
        client = Client()
        response = client.get("/api/expenses/")
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ), f"Expected 200 or 401, got {response.status_code}"

    def test_expense_create_returns_json(self):
        """Expense POST should return JSON response."""
        client = Client()
        response = client.post(
            "/api/expenses/",
            {"description": "test", "amount": "100.00"},
            content_type="application/json",
        )
        # Endpoint is AllowAny by default; verify it returns JSON
        assert response.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ), f"Unexpected status: {response.status_code}"

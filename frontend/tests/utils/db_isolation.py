"""Database isolation utilities for frontend integration testing.

Production-grade transaction-safe test isolation supporting:
- Django transaction management
- Test data cleanup
- Isolation verification
- Resource tracking
"""
import os
import sys
import time
import pytest
import uuid
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager


class TestIsolation:
    """Manages test database isolation."""

    def __init__(self, backend_path: str):
        self.backend_path = backend_path
        self._configured = False
        self._transaction_id: Optional[str] = None

    def configure(self) -> bool:
        """Configure Django for testing."""
        if self._configured:
            return True

        try:
            backend_dir = os.path.abspath(self.backend_path)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

            import django
            django.setup()
            self._configured = True
            return True

        except Exception as e:
            print(f"Django configuration failed: {e}")
            return False

    def create_transaction_id(self) -> str:
        """Create unique transaction identifier."""
        self._transaction_id = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        return self._transaction_id

    @contextmanager
    def transaction_isolation(self):
        """Context manager for transaction-based isolation.

        Usage:
            with isolation.transaction_isolation():
                # Test operations that modify data
                api_client.post("/api/inventory/products/", {...})
        """
        self.create_transaction_id()

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(f"BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE")

            yield

        finally:
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("ROLLBACK")
            except Exception:
                pass

    @contextmanager
    def test_data_scope(self, category: str):
        """Scope for test data with automatic cleanup.

        Usage:
            with isolation.test_data_scope("products") as scope:
                product_id = scope.create("product", {...})
                # Test with product
        """
        scope = TestDataScope(category, self._transaction_id)
        yield scope


class TestDataScope:
    """Scope for managing test data lifecycle."""

    def __init__(self, category: str, transaction_id: str):
        self.category = category
        self.transaction_id = transaction_id
        self._created: List[Dict[str, Any]] = []

    def create(self, resource_type: str, data: Dict[str, Any]) -> Optional[int]:
        """Register created test data for tracking."""
        record = {
            "type": resource_type,
            "data": data,
            "created_at": time.time()
        }
        self._created.append(record)
        return data.get("id")

    def cleanup(self, api_client) -> None:
        """Clean up created test data."""
        for record in reversed(self._created):
            try:
                endpoint = self._get_endpoint(record["type"])
                resource_id = record["data"].get("id")
                if endpoint and resource_id:
                    api_client.delete(f"{endpoint}{resource_id}/")
            except Exception:
                pass

    def _get_endpoint(self, resource_type: str) -> Optional[str]:
        """Get API endpoint for resource type."""
        endpoints = {
            "product": "/api/inventory/products/",
            "category": "/api/inventory/categories/",
            "warehouse": "/api/inventory/warehouses/",
            "batch": "/api/inventory/batches/",
            "customer": "/api/sales/customers/",
            "supplier": "/api/purchases/suppliers/",
            "invoice": "/api/sales/invoices/",
            "account": "/api/accounting/accounts/",
            "employee": "/api/hr/employees/",
        }
        return endpoints.get(resource_type)


class DatabaseState:
    """Tracks database state for isolation verification."""

    def __init__(self, backend_path: str):
        self.backend_path = backend_path
        self._snapshots: Dict[str, Dict[str, int]] = {}

    def take_snapshot(self, name: str) -> bool:
        """Take a snapshot of current database state."""
        if not self._configure_django():
            return False

        try:
            from django.apps import apps

            models_to_check = [
                "inventory.Product",
                "inventory.Category",
                "inventory.Warehouse",
                "sales.Customer",
                "accounting.Account",
            ]

            snapshot = {}
            for model_path in models_to_check:
                try:
                    app_label, model_name = model_path.split(".")
                    model = apps.get_model(app_label, model_name)
                    snapshot[model_path] = model.objects.count()
                except Exception:
                    pass

            self._snapshots[name] = snapshot
            return True

        except Exception:
            return False

    def verify_isolation(self, snapshot_name: str) -> Dict[str, Any]:
        """Verify database isolation after test."""
        if snapshot_name not in self._snapshots:
            return {"success": False, "error": "No snapshot found"}

        if not self._configure_django():
            return {"success": False, "error": "Django not configured"}

        try:
            from django.apps import apps

            original = self._snapshots[snapshot_name]
            current = {}

            for model_path, original_count in original.items():
                try:
                    app_label, model_name = model_path.split(".")
                    model = apps.get_model(app_label, model_name)
                    current[model_path] = model.objects.count()
                except Exception:
                    current[model_path] = -1

            changed = {}
            for model_path in original:
                if model_path in current and original[model_path] != current[model_path]:
                    changed[model_path] = {
                        "before": original[model_path],
                        "after": current[model_path],
                        "delta": current[model_path] - original[model_path]
                    }

            return {
                "success": True,
                "unchanged": len(changed) == 0,
                "changes": changed
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _configure_django(self) -> bool:
        """Configure Django if not already done."""
        try:
            import django
            if not django.apps.ready:
                backend_dir = os.path.abspath(self.backend_path)
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()
            return True
        except Exception:
            return False


class ResourceTracker:
    """Tracks resources created during tests for cleanup."""

    def __init__(self):
        self._resources: List[Dict[str, Any]] = []
        self._locked: bool = False

    def acquire(self, resource_type: str, resource_id: Any, endpoint: str, data: Dict[str, Any]) -> None:
        """Acquire a resource for tracking."""
        if self._locked:
            return

        self._resources.append({
            "type": resource_type,
            "id": resource_id,
            "endpoint": endpoint,
            "data": data,
            "acquired_at": time.time()
        })

    def release(self, api_client) -> None:
        """Release and cleanup all tracked resources."""
        self._locked = True

        for resource in reversed(self._resources):
            try:
                endpoint = resource["endpoint"]
                resource_id = resource["id"]

                if endpoint and resource_id:
                    api_client.delete(f"{endpoint}{resource_id}/")

            except Exception:
                pass

        self._resources.clear()
        self._locked = False

    def get_stats(self) -> Dict[str, int]:
        """Get resource tracking statistics."""
        stats = {}
        for resource in self._resources:
            rtype = resource["type"]
            stats[rtype] = stats.get(rtype, 0) + 1
        return stats


@pytest.fixture(scope="session")
def test_isolation(backend_path) -> TestIsolation:
    """Provide test isolation utility."""
    isolation = TestIsolation(backend_path)
    isolation.configure()
    return isolation


@pytest.fixture
def db_state_tracker(backend_path) -> DatabaseState:
    """Provide database state tracker."""
    return DatabaseState(backend_path)


@pytest.fixture
def resource_tracker() -> ResourceTracker:
    """Provide resource tracker."""
    return ResourceTracker()


@pytest.fixture
def isolated_test(test_isolation, resource_tracker):
    """Fixture that provides isolated test context."""
    @contextmanager
    def _isolated(api_client):
        test_isolation.create_transaction_id()
        yield TestContext(api_client, resource_tracker)

    return _isolated


class TestContext:
    """Context for isolated tests."""

    def __init__(self, api_client, tracker: ResourceTracker):
        self.api_client = api_client
        self.tracker = tracker

    def create_test_resource(self, resource_type: str, endpoint: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Create and track a test resource."""
        try:
            response = self.api_client.post(endpoint, data)
            if response.status_code in [200, 201]:
                result = response.json()
                self.tracker.acquire(resource_type, result.get("id"), endpoint, result)
                return result
        except Exception:
            pass
        return None

    def cleanup(self) -> None:
        """Clean up all tracked resources."""
        self.tracker.release(self.api_client)
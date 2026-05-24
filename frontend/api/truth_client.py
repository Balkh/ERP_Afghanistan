"""
Phase 5B.6 — Truth Layer API Client.

Provides typed access to:
- Event Store (emit, query, list)
- Truth verification (claim, existence, aggregate)
- Reports (stock, ledger, trial balance, employees, orders)
"""
from typing import Optional
from api.client import APIClient


class TruthAPIClient:
    """Typed client for Truth Layer API endpoints."""

    def __init__(self, client: APIClient):
        self._c = client
        self._base = "/api/v1/truth"

    # ─── Events ───

    def emit_event(self, domain: str, event_type: str, aggregate_id: str,
                   payload: dict, source_type: str = "REAL",
                   metadata: dict = None) -> str:
        resp = self._c.post(f"{self._base}/events/emit/", {
            "domain": domain, "event_type": event_type,
            "aggregate_id": aggregate_id, "payload": payload,
            "source_type": source_type, "metadata": metadata or {},
        })
        return resp.get("data", {}).get("event_id", "") if isinstance(resp, dict) else ""

    def list_events(self, domain: str = None, source_type: str = None,
                    aggregate_id: str = None, limit: int = 100) -> list:
        params = {"limit": limit}
        if domain: params["domain"] = domain
        if source_type: params["source_type"] = source_type
        if aggregate_id: params["aggregate_id"] = aggregate_id
        resp = self._c.get(f"{self._base}/events/", params=params)
        return resp.get("data", {}).get("events", []) if isinstance(resp, dict) else []

    def get_event(self, event_id: str) -> Optional[dict]:
        resp = self._c.get(f"{self._base}/events/{event_id}/")
        return resp.get("data") if isinstance(resp, dict) and resp.get("success") else None

    def event_exists(self, event_id: str) -> bool:
        resp = self._c.get(f"{self._base}/events/{event_id}/exists/")
        return resp.get("data", {}).get("exists", False) if isinstance(resp, dict) else False

    # ─── Verification ───

    def verify_claim(self, event_type: str, aggregate_id: str,
                     domain: str = "inventory", expected_count: int = 1) -> dict:
        return self._c.post(f"{self._base}/verify/", {
            "event_type": event_type, "aggregate_id": aggregate_id,
            "domain": domain, "expected_count": expected_count,
        })

    def verify_aggregate(self, domain: str, aggregate_id: str) -> dict:
        return self._c.get(f"{self._base}/verify/{domain}/{aggregate_id}/")

    # ─── Reports ───

    def get_stock_levels(self) -> dict:
        return self._c.get(f"{self._base}/reports/stock-levels/")

    def get_ledger(self) -> dict:
        return self._c.get(f"{self._base}/reports/ledger/")

    def get_trial_balance(self) -> dict:
        return self._c.get(f"{self._base}/reports/trial-balance/")

    def get_employees(self) -> dict:
        return self._c.get(f"{self._base}/reports/employees/")

    def get_orders(self) -> dict:
        return self._c.get(f"{self._base}/reports/orders/")

    # ─── System ───

    def get_summary(self) -> dict:
        return self._c.get(f"{self._base}/summary/")

    def check_consistency(self) -> dict:
        return self._c.get(f"{self._base}/consistency/")

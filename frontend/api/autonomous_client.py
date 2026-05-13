"""
Phase 5B.9 — Autonomous Intelligence API Client.

Typed client for Phase 5B.8 autonomous intelligence endpoints.
All responses are read-only intelligence data.
"""
from typing import Any, Dict, List, Optional
from api.client import APIClient


class AutonomousAPIClient:
    """Typed client for Autonomous Intelligence API endpoints."""

    def __init__(self, client: APIClient):
        self._c = client
        self._base = "/api/v1/autonomous"

    def get_insights(self, domain: str = "") -> dict:
        params = {}
        if domain: params["domain"] = domain
        return self._c.get(f"{self._base}/insights/", params=params)

    def get_risk_summary(self) -> dict:
        return self._c.get(f"{self._base}/risk-summary/")

    def get_decision_options(self) -> dict:
        return self._c.get(f"{self._base}/decision-options/")

    def get_forecasts(self) -> dict:
        return self._c.get(f"{self._base}/forecast/")

    def get_anomaly_warnings(self) -> dict:
        return self._c.get(f"{self._base}/anomaly-warnings/")

    def get_full_report(self, domain: str = "enterprise") -> dict:
        return self._c.get(f"{self._base}/report/", params={"domain": domain})

    def get_recommendations(self) -> dict:
        return self._c.get(f"{self._base}/recommendations/")

    def get_status(self) -> dict:
        return self._c.get(f"{self._base}/status/")

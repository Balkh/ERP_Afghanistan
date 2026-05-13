"""
Phase 5B.6 — Intelligence API Client.

Provides typed access to:
- Drift detection (baseline, drift scores, velocity)
- Pattern mining (sequences, rare, bursts)
- Anomaly graphs (cross-domain)
- Temporal drift analysis
- Consistency deviation analysis
"""
from typing import Any, Dict, List, Optional
from api.client import APIClient


class IntelligenceAPIClient:
    """Typed client for Intelligence API endpoints."""

    def __init__(self, client: APIClient):
        self._c = client
        self._base = "/api/v1/intelligence"

    # ─── Drift ───

    def get_baseline(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/drift/baseline/{domain}/")

    def get_aggregate_drift(self, domain: str, aggregate_id: str) -> dict:
        return self._c.get(f"{self._base}/drift/{domain}/{aggregate_id}/")

    def get_all_drift(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/drift/{domain}/")

    # ─── Patterns ───

    def get_patterns(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/patterns/{domain}/")

    def get_rare_events(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/patterns/{domain}/rare/")

    def get_bursts(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/patterns/{domain}/bursts/")

    # ─── Anomaly Graph ───

    def get_anomaly_graph(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/anomalies/{domain}/")

    def get_cross_domain_graph(self) -> dict:
        return self._c.get(f"{self._base}/anomalies/cross-domain/")

    # ─── Temporal ───

    def get_temporal_drift(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/temporal/{domain}/")

    # ─── Consistency ───

    def get_consistency(self) -> dict:
        return self._c.get(f"{self._base}/consistency/")

    def compare_consistency(self, truth_layer_counts: dict) -> dict:
        return self._c.post(f"{self._base}/consistency/compare/", {
            "truth_layer_counts": truth_layer_counts,
        })

    # ─── System ───

    def get_snapshot(self) -> dict:
        return self._c.get(f"{self._base}/snapshot/")

    def get_status(self) -> dict:
        return self._c.get(f"{self._base}/status/")

"""
Phase 5B.6 — Observability API Client.

Provides typed access to:
- Trace (aggregate lifecycle, causation graphs)
- Timeline (deterministic event timelines)
- Correlation (cross-domain links)
- Integrity (system health)
- Replay (time-travel)
- Dashboard (read-only views)
"""
from typing import Any, Dict, List, Optional
from api.client import APIClient


class ObservabilityAPIClient:
    """Typed client for Observability API endpoints."""

    def __init__(self, client: APIClient):
        self._c = client
        self._base = "/api/v1/observability"

    # ─── Trace ───

    def trace_aggregate(self, domain: str, aggregate_id: str) -> dict:
        return self._c.get(f"{self._base}/trace/{domain}/{aggregate_id}/")

    def trace_by_event(self, event_id: str) -> Optional[dict]:
        resp = self._c.get(f"{self._base}/trace/event/{event_id}/")
        return resp.get("data") if isinstance(resp, dict) and resp.get("success") else None

    def causation_graph(self, event_id: str) -> dict:
        return self._c.get(f"{self._base}/trace/{event_id}/causation/")

    # ─── Timeline ───

    def get_timeline(self, from_ts: str = "", to_ts: str = "",
                     domains: list = None, max_entries: int = 500) -> dict:
        params = {"max": max_entries}
        if from_ts: params["from"] = from_ts
        if to_ts: params["to"] = to_ts
        if domains: params["domains"] = domains
        return self._c.get(f"{self._base}/timeline/", params=params)

    def get_aggregate_timeline(self, domain: str, aggregate_id: str) -> dict:
        return self._c.get(f"{self._base}/timeline/{domain}/{aggregate_id}/")

    # ─── Correlation ───

    def get_correlation(self, event_id: str) -> dict:
        return self._c.get(f"{self._base}/correlation/{event_id}/")

    def get_domain_correlation(self, domain_a: str, domain_b: str) -> dict:
        return self._c.get(f"{self._base}/correlation/{domain_a}/{domain_b}/")

    def get_domain_dependencies(self) -> dict:
        return self._c.get(f"{self._base}/correlation/dependencies/")

    # ─── Integrity ───

    def check_integrity(self) -> dict:
        return self._c.get(f"{self._base}/integrity/")

    def get_domain_integrity(self, domain: str) -> dict:
        return self._c.get(f"{self._base}/integrity/{domain}/")

    # ─── Replay ───

    def get_replay_state(self, from_seq: int = 0, to_seq: int = None) -> dict:
        params = {"from": from_seq}
        if to_seq is not None: params["to"] = to_seq
        return self._c.get(f"{self._base}/replay/", params=params)

    def render_at_sequence(self, sequence: int) -> dict:
        return self._c.get(f"{self._base}/replay/render/{sequence}/")

    def get_replay_hash(self, from_seq: int, to_seq: int) -> dict:
        return self._c.get(f"{self._base}/replay/hash/",
                           params={"from": from_seq, "to": to_seq})

    # ─── Dashboard ───

    def get_dashboard(self, dashboard_type: str = "overview",
                      domain: str = "inventory") -> dict:
        return self._c.get(f"{self._base}/dashboard/{dashboard_type}/",
                           params={"domain": domain})

    def get_snapshot(self) -> dict:
        return self._c.get(f"{self._base}/snapshot/")

    def get_status(self) -> dict:
        return self._c.get(f"{self._base}/status/")

    def get_stream_metrics(self) -> dict:
        return self._c.get(f"{self._base}/stream/")

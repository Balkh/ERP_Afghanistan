import time
from datetime import datetime
from typing import Dict, Any, Optional

from api.client import APIClient


class ControlCenterService:
    """
    Service layer for Control Center.
    Supports single BFF bundle (Sprint 2) or legacy per-endpoint fetch.
    """

    def __init__(self, base_url: str = "http://localhost:8000", api_client=None):
        self.base_url = base_url.rstrip("/")
        self._api = api_client or APIClient()
        self._cache: Dict[str, Any] = {}

    def _normalize_response(self, status: str, data: Any = None, error: str = "") -> Dict[str, Any]:
        return {
            "status": status,
            "data": data or {},
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

    def _fetch_hub_bundle(self) -> Optional[Dict[str, Any]]:
        """Single round-trip via authenticated API client."""
        try:
            res = self._api.get(
                "/api/control-center/hub-bundle/",
                background=True,
                retries=1,
            )
            if isinstance(res, dict) and res.get("success") is False:
                return None
            bundle = res.get("data", res) if isinstance(res, dict) else res
            if not isinstance(bundle, dict):
                return None
            return {
                "health": self._normalize_response("ok", bundle.get("health", {})),
                "intelligence": self._normalize_response("ok", bundle.get("intelligence", {})),
                "signals": self._normalize_response("ok", bundle.get("signals", [])),
                "jobs": self._normalize_response("ok", bundle.get("jobs", {})),
                "financial": self._normalize_response("ok", bundle.get("financial", {})),
                "inventory": self._normalize_response("ok", bundle.get("inventory", {})),
                "ops": self._normalize_response("ok", bundle.get("operations", {})),
                "stats": self._normalize_response("ok", bundle.get("stats", {})),
                "workflows": self._normalize_response(
                    "ok",
                    bundle.get("workflows_pending", bundle.get("workflow_instances", [])),
                ),
                "_bundle_raw": bundle,
            }
        except Exception:
            return None

    def fetch_endpoint(self, key: str, url: str, timeout: int = 8, retries: int = 2) -> Dict[str, Any]:
        attempt = 0

        while attempt <= retries:
            try:
                res = self._api.get(url, background=True, retries=0)

                if isinstance(res, dict) and res.get("success") is False:
                    attempt += 1
                    if attempt <= retries:
                        time.sleep(0.5 * attempt)
                        continue
                    return self._normalize_response(
                        "unavailable",
                        data=self._cache.get(key),
                        error=res.get("error", "Request failed"),
                    )

                data = res.get("data", res) if isinstance(res, dict) and "success" in res else res
                self._cache[key] = data
                return self._normalize_response("ok", data=data)

            except Exception as e:
                attempt += 1
                if attempt <= retries:
                    time.sleep(0.5 * attempt)
                    continue
                return self._normalize_response(
                    "unavailable",
                    data=self._cache.get(key),
                    error=str(e),
                )

        return self._normalize_response("unavailable", data=self._cache.get(key), error="Max retries reached")

    def get_dashboard_data(self) -> Dict[str, Any]:
        bundled = self._fetch_hub_bundle()
        if bundled:
            return bundled

        endpoints = {
            "health": "/api/control-center/health/",
            "intelligence": "/api/control-center/intelligence/",
            "signals": "/api/control-center/signals/active/",
            "jobs": "/api/control-center/jobs/",
            "financial": "/api/control-center/financial/",
            "inventory": "/api/control-center/inventory/",
            "ops": "/api/control-center/operations/",
            "stats": "/api/control-center/stats/",
            "workflows": "/api/workflows/my-pending/",
        }

        results = {}
        for key, url in endpoints.items():
            is_critical = key in ["health", "ops", "stats"]
            results[key] = self.fetch_endpoint(key, url, retries=2 if is_critical else 1)

        return results

    def get_hub_bundle_raw(self) -> Optional[Dict[str, Any]]:
        """Full bundle for Correlation / Workflow consumers."""
        data = self.get_dashboard_data()
        return data.get("_bundle_raw")

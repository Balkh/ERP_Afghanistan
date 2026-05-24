import time
import requests
from datetime import datetime
from typing import Dict, Any

class ControlCenterService:
    """
    Service layer for Control Center.
    Handles resilient API communication with timeouts, retries, and normalized responses.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json; version=v1"
        })
        # Cache for last known good values
        self._cache: Dict[str, Any] = {}

    def _normalize_response(self, status: str, data: Any = None, error: str = "") -> Dict[str, Any]:
        """Standardize the response format."""
        return {
            "status": status,  # "ok", "error", "unavailable"
            "data": data or {},
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

    def fetch_endpoint(self, key: str, url: str, timeout: int = 8, retries: int = 2) -> Dict[str, Any]:
        """
        Fetch a single endpoint with retry logic and timeout.
        """
        full_url = f"{self.base_url}{url}"
        attempt = 0
        
        while attempt <= retries:
            try:
                response = self.session.get(full_url, timeout=timeout)
                
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        # Handle standardized backend wrapper
                        data = res_json.get('data', res_json) if isinstance(res_json, dict) and 'success' in res_json else res_json
                        
                        # Update cache with last known good value
                        self._cache[key] = data
                        return self._normalize_response("ok", data=data)
                    except ValueError:
                        return self._normalize_response("error", error="Invalid JSON response")
                
                # If not 200, maybe retry
                attempt += 1
                if attempt <= retries:
                    time.sleep(0.5 * attempt) # Simple backoff
                    continue
                
                return self._normalize_response("unavailable", 
                                             data=self._cache.get(key), 
                                             error=f"HTTP {response.status_code}")

            except requests.exceptions.RequestException as e:
                attempt += 1
                if attempt <= retries:
                    time.sleep(0.5 * attempt)
                    continue
                
                return self._normalize_response("unavailable", 
                                             data=self._cache.get(key), 
                                             error=str(e))
        
        return self._normalize_response("unavailable", data=self._cache.get(key), error="Max retries reached")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Fetch all dashboard components. 
        Each component is fetched independently to support partial data rendering.
        """
        endpoints = {
            'health': '/api/control-center/health/',
            'intelligence': '/api/control-center/intelligence/',
            'signals': '/api/control-center/signals/active/',
            'jobs': '/api/control-center/jobs/',
            'financial': '/api/control-center/financial/',
            'inventory': '/api/control-center/inventory/',
            'ops': '/api/control-center/operations/',
            'stats': '/api/control-center/stats/',
            'workflows': '/api/workflows/my-pending/'
        }
        
        results = {}
        for key, url in endpoints.items():
            # Critical endpoints get more retries, others less
            is_critical = key in ['health', 'ops', 'stats']
            results[key] = self.fetch_endpoint(key, url, retries=2 if is_critical else 1)
            
        return results

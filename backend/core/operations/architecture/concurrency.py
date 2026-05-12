"""
Phase 5A.5.5 — Concurrency Boundary Map.

Maps all thread interaction points, shared state,
and isolation boundaries in the operational runtime.

No runtime mutation. Deterministic output.
"""
from typing import Any, Dict, List


THREAD_BOUNDARIES = {
    "ui_thread": {
        "process": "PySide6 QApplication event loop",
        "responsibilities": [
            "Widget rendering",
            "User input handling",
            "Timer-based data refresh (AsyncDataLoader)",
            "Signal emission (data_loaded, load_error, state_changed)",
        ],
        "never": [
            "Block on synchronous API calls",
            "Execute ERP mutations",
            "Modify engine state directly",
        ],
        "safety_mechanisms": [
            "AsyncDataLoader with QTimer (non-blocking polling)",
            "BaseViewModel signals for thread-safe state updates",
            "ViewState enum prevents stale mutation",
            "5000ms default poll interval prevents timer saturation",
        ],
    },
    "api_thread": {
        "process": "Django/DRF request handling (WSGI/ASGI)",
        "responsibilities": [
            "HTTP request parsing",
            "Authentication (JWT + Session)",
            "Permission checking (IsAuthenticated + custom)",
            "Observability endpoint execution",
            "StandardizedJSONResponse rendering",
        ],
        "never": [
            "Access ERP models for mutation",
            "Bypass read-only guards",
            "Modify global state",
        ],
        "safety_mechanisms": [
            "All observability endpoints are GET-only",
            "Response.observability_read_only flag",
            "Custom exception handler catches all errors",
            "Lazy singleton engines (thread-safe after init)",
        ],
    },
    "engine_thread": {
        "process": "ControlCenterEngine signal processing (synchronous within API handler)",
        "responsibilities": [
            "Signal ingestion and processing",
            "State aggregation and classification",
            "Incident registration and escalation",
            "Timeline event management",
            "Dashboard snapshot generation",
            "Safety report generation",
        ],
        "never": [
            "Execute ERP mutations",
            "Bypass bounded memory containers",
            "Allow unbounded growth",
        ],
        "safety_mechanisms": [
            "All containers use deque(maxlen=...)",
            "Exception-safe processing (try/except wrappers)",
            "Depth check prevents unlimited orchestration",
            "clear() resets all state",
        ],
    },
}


SHARED_STATE_INVENTORY = {
    "no_shared_mutable_state": True,
    "singleton_engines": {
        "purpose": "Lazy-init engine instances in observability views",
        "thread_safety": "Only accessed from API thread (per-request)",
        "reset_mechanism": "Module reload (no production reset needed)",
    },
    "api_response_attributes": {
        "observability_read_only": "Set per-response, never shared",
        "observability_meta_extras": "Set per-response, never shared",
    },
}


def get_concurrency_boundary_map() -> Dict[str, Any]:
    """Return the complete concurrency boundary map."""
    return {
        "thread_boundaries": THREAD_BOUNDARIES,
        "shared_state": SHARED_STATE_INVENTORY,
        "deadlock_prevention": [
            "No lock-based synchronization (single-threaded engine)",
            "No blocking waits in UI thread (QTimer-based polling)",
            "No circular dependencies in engine subcomponents",
            "clear() operation does not wait for pending operations",
        ],
        "starvation_prevention": [
            "Bounded processing depth (100000 max orchestration)",
            "Bounded deque containers prevent infinite memory growth",
            "Safety guards detect and log excessive recursion",
        ],
    }


def get_thread_interaction_inventory() -> List[Dict[str, str]]:
    """Return the inventory of all thread interaction points."""
    return [
        {
            "from_thread": "ui_thread",
            "to_thread": "api_thread",
            "mechanism": "AsyncDataLoader._api_client.get() via QTimer",
            "direction": "ui → api (HTTP request)",
            "safety": "QTimer prevents queue saturation; default 5000ms interval",
        },
        {
            "from_thread": "api_thread",
            "to_thread": "engine_thread",
            "mechanism": "Synchronous call to ControlCenterEngine methods",
            "direction": "api → engine (direct method call)",
            "safety": "Engine is single-threaded, no reentrancy issues",
        },
        {
            "from_thread": "api_thread",
            "to_thread": "ui_thread",
            "mechanism": "JSON response rendered back to HTTP client",
            "direction": "api → ui (HTTP response)",
            "safety": "StandardizedJSONRenderer wraps response deterministically",
        },
    ]

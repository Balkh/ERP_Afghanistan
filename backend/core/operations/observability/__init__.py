"""
Phase 5B.4 — Enterprise Observability & Operational Control Layer.

REAL-TIME VISIBILITY • AUDITABLE EXECUTION TRACE • SYSTEM-WIDE INTROSPECTION

Core principle:
    "Everything is observable. Nothing is controllable."

This layer is PURE READ-ONLY. It NEVER:
- modifies ERP state
- executes business actions
- alters events
- mutates projections
- overrides governance decisions
- interferes with truth/ingestion layers
"""
OBSERVABILITY_LAYER_VERSION = "1.0.0"

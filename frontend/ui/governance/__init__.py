"""
Phase 16 — UI Governance & Design System Enforcement Package.

Core modules:
- registry: Approved UI primitives registry (single source of truth)
- audit_scanner: Static violation detection (raw colors, forbidden widgets, etc.)
- consistency_audit: Pattern consistency scoring (typography, hierarchy, etc.)
"""

from .registry import REGISTRY, Primitive, ComponentCategory, is_approved, get_primitive
from .audit_scanner import GovernanceScanner, ScanReport, Violation, Severity
from .consistency_audit import ConsistencyEngine, ConsistencyReport

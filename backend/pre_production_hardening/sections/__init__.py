"""
Pre-Production Hardening - Validation Sections

Each module in this package contains a single `run(validator)` function
that performs one validation section. The `PreProductionHardeningValidator`
class methods delegate to these functions; the public API of the class is
preserved exactly.

Public-API contract (must remain identical to pre-refactor):
- run(validator) -> SectionResult
- Each function mutates validator.issues (extends) and validator.results (assigns)
"""
from pre_production_hardening.sections.database import run as run_database
from pre_production_hardening.sections.multi_user import run as run_multi_user
from pre_production_hardening.sections.operator import run as run_operator
from pre_production_hardening.sections.session import run as run_session
from pre_production_hardening.sections.export import run as run_export
from pre_production_hardening.sections.deployment import run as run_deployment
from pre_production_hardening.sections.performance import run as run_performance
from pre_production_hardening.sections.report import run as run_report

__all__ = [
    "run_database",
    "run_multi_user",
    "run_operator",
    "run_session",
    "run_export",
    "run_deployment",
    "run_performance",
    "run_report",
]

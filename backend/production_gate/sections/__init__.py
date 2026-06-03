"""Section modules for production_gate validator.
Each module exports a `run(self)` function that takes the validator
instance, mutates `validator.issues` and `validator.results`, and returns
the SectionResult.
"""
from production_gate.sections.frontend import run as run_frontend
from production_gate.sections.workflows import run as run_workflows
from production_gate.sections.concurrency import run as run_concurrency
from production_gate.sections.failure_injection import run as run_failure_injection
from production_gate.sections.backup_restore import run as run_backup_restore
from production_gate.sections.long_run import run as run_long_run

__all__ = [
    "run_frontend",
    "run_workflows",
    "run_concurrency",
    "run_failure_injection",
    "run_backup_restore",
    "run_long_run",
]

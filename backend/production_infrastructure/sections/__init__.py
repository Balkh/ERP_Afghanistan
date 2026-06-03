"""Section modules for production_infrastructure validator.
Each module exports a `run(validator)` function that takes the validator
instance, mutates `validator.issues` and `validator.results`, and returns
the SectionResult (or final dict for certification).
"""
from production_infrastructure.sections.postgresql import run as run_postgresql
from production_infrastructure.sections.transaction_isolation import run as run_transaction_isolation
from production_infrastructure.sections.connection_pooling import run as run_connection_pooling
from production_infrastructure.sections.redis_event_layer import run as run_redis_event_layer
from production_infrastructure.sections.celery_execution import run as run_celery_execution
from production_infrastructure.sections.security_hardening import run as run_security_hardening
from production_infrastructure.sections.backup_automation import run as run_backup_automation
from production_infrastructure.sections.performance import run as run_performance
from production_infrastructure.sections.observability import run as run_observability
from production_infrastructure.sections.certification import run as run_certification

__all__ = [
    "run_postgresql",
    "run_transaction_isolation",
    "run_connection_pooling",
    "run_redis_event_layer",
    "run_celery_execution",
    "run_security_hardening",
    "run_backup_automation",
    "run_performance",
    "run_observability",
    "run_certification",
]

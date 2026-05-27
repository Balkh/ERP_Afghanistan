import os
import logging
from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger('erp.system')


def auto_bootstrap(sender, **kwargs):
    """Automatically seed roles + assign admin roles after migration."""
    try:
        from core.governance.bootstrap import BootstrapOrchestrator
        orch = BootstrapOrchestrator()
        results = orch.execute()
        for r in results:
            if r["status"] in ("failed", "error"):
                logger.warning(f"Auto-bootstrap {r['step']}: {r['status']} - {r['detail']}")
    except Exception as e:
        logger.warning(f"Auto-bootstrap skipped (first migration?): {e}")


def run_readiness_check(sender, **kwargs):
    """Run readiness validation after migration completes."""
    try:
        from core.governance.readiness import get_full_readiness
        report = get_full_readiness(include_integrity=False)
        if report.blockers:
            logger.warning(f"Post-migration readiness: {len(report.blockers)} blocker(s)")
            for b in report.blockers:
                logger.warning(f"  BLOCKER: {b}")
        if report.warnings:
            logger.warning(f"Post-migration readiness: {len(report.warnings)} warning(s)")
            for w in report.warnings:
                logger.warning(f"  WARN: {w}")
        logger.info(f"Post-migration readiness overall: {report.overall}")
    except Exception as e:
        logger.warning(f"Post-migration readiness check skipped: {e}")


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Foundation'

    def ready(self):
        self._run_startup_diagnostics()
        self._register_checks()
        self._connect_post_migrate()

    def _register_checks(self):
        """Register Django system checks for enterprise governance."""
        try:
            import core.checks  # noqa: F401
            logger.debug("Enterprise governance checks registered")
        except Exception:
            pass

    def _connect_post_migrate(self):
        """Connect post_migrate signal for auto-bootstrap + readiness."""
        post_migrate.connect(auto_bootstrap, sender=self)
        post_migrate.connect(run_readiness_check, sender=self)
        logger.debug("Post-migrate hooks connected: auto-bootstrap + readiness")

    def _run_startup_diagnostics(self):
        """Run startup health checks and log results."""
        logger.info("=== Startup Diagnostics ===")

        try:
            from core.operations.health import HealthMonitor
            db = HealthMonitor.check_database()
            db_status = db.get('status', 'unknown')
            if db_status == 'healthy':
                latency = db.get('checks', {}).get('connection', {}).get('latency_ms', '?')
                logger.info(f"  DB health: {db_status} (latency: {latency}ms)")
            else:
                issues = db.get('issues', [])
                for issue in issues:
                    logger.warning(f"  DB issue: {issue}")

            system = HealthMonitor.check_system()
            sys_status = system.get('status', 'unknown')
            logger.info(f"  System health: {sys_status}")
            for issue in system.get('issues', []):
                logger.warning(f"  System issue: {issue}")

            services = HealthMonitor.check_background_services()
            srv_status = services.get('status', 'unknown')
            logger.info(f"  Services health: {srv_status}")

            logger.info(f"  Overall: DB={db_status}, System={sys_status}, Services={srv_status}")
        except Exception as e:
            logger.warning(f"Startup diagnostics incomplete: {e}")

        logger.info("=== Startup Diagnostics Complete ===")

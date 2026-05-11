import logging
from django.apps import AppConfig

logger = logging.getLogger('erp.system')


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Foundation'

    def ready(self):
        self._run_startup_diagnostics()

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
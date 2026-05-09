"""Status module - System status monitoring."""
from .health import HealthChecker


class StatusChecker:
    """Check system status."""

    def __init__(self, backend_dir):
        self.health_checker = HealthChecker(backend_dir)

    def check_status(self) -> dict:
        """Check full system status."""
        status = {
            "backend": "stopped",
            "frontend": "stopped",
            "api": "unavailable",
            "db": "unavailable"
        }

        # Check DB
        if self.health_checker.check_db_connection():
            status["db"] = "connected"

        # Check API
        if self.health_checker.check_backend_api():
            status["api"] = "healthy"
            status["backend"] = "running"

        return status
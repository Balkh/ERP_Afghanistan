"""Health check module."""
import subprocess
import socket
import sys
from pathlib import Path


class HealthChecker:
    """System health verification."""

    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir

    def check_port(self, port: int) -> bool:
        """Check if port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def check_db_connection(self) -> bool:
        """Check database connectivity."""
        try:
            result = subprocess.run(
                [sys.executable, "manage.py", "shell", "-c",
                 "from django.db import connection; connection.ensure_connection(); print('OK')"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0 and "OK" in result.stdout
        except Exception:
            return False

    def check_backend_api(self) -> bool:
        """Check if backend API responds."""
        try:
            import requests
            resp = requests.get("http://localhost:8000/api/ops/health/", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def run_health_check(self) -> dict:
        """Run all health checks."""
        checks = {
            "Database": self.check_db_connection(),
            "Port 8000 available": self.check_port(8000),
        }

        results = {
            "passed": all(checks.values()),
            "checks": checks
        }

        return results
"""Orchestrator - Main runner coordinator."""
import sys
from pathlib import Path
from .startup import StartupManager
from .health import HealthChecker
from .tests import TestRunner
from .status import StatusChecker


class ERPRunner:
    """Unified ERP system orchestration."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.backend_dir = self.base_dir / "backend"
        self.frontend_dir = self.base_dir / "frontend"

        self.startup = StartupManager(self.backend_dir, self.frontend_dir)
        self.health = HealthChecker(self.backend_dir)
        self.tests = TestRunner(self.backend_dir)
        self.status = StatusChecker(self.backend_dir)

    @property
    def check_status(self):
        return self.status.check_status

    @property
    def run_health_check(self):
        return self.health.run_health_check

    @property
    def start_backend(self):
        return self.startup.start_backend

    @property
    def start_frontend(self):
        return self.startup.start_frontend

    @property
    def stop_backend(self):
        return self.startup.stop_backend

    @property
    def stop_frontend(self):
        return self.startup.stop_frontend

    @property
    def run_tests(self):
        return self.tests.run_tests

    @property
    def run_backend_tests(self):
        return self.tests.run_backend_tests

    @property
    def run_integration_tests(self):
        return self.tests.run_integration_tests

    def start_full_system(self):
        """Start complete system."""
        print("=" * 50)
        print("START Starting Full ERP System")
        print("=" * 50)

        if not self.health.run_health_check()["passed"]:
            print("[!] Health check had issues but continuing...")

        if not self.startup.start_backend():
            print("[X] Cannot start backend. Exiting.")
            return

        self.startup.start_frontend()

        print("\n" + "=" * 50)
        print("[OK] System running!")
        print("  Backend: http://localhost:8000")
        print("  API: http://localhost:8000/api/")
        print("=" * 50)

    def cleanup(self):
        """Stop all processes."""
        self.startup.cleanup()
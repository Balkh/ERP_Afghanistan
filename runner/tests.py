"""Test runner module."""
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """Run Django tests."""

    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir

    def run_tests(self, test_path: str = "tests", verbosity: int = 1) -> dict:
        """Run Django tests."""
        print(f"TEST Running tests: {test_path}...")
        start_time = time.time()

        result = subprocess.run(
            [sys.executable, "manage.py", "test", test_path, "-v", str(verbosity)],
            cwd=str(self.backend_dir),
            capture_output=True,
            text=True
        )

        elapsed = time.time() - start_time
        output = result.stdout + result.stderr
        passed = "OK" in output and "FAIL" not in output[:500]
        failed_count = output.count("FAIL:")

        return {
            "passed": passed,
            "failed_count": failed_count,
            "elapsed": round(elapsed, 2),
            "output": output[-2000:]
        }

    def run_backend_tests(self) -> dict:
        """Run core backend tests."""
        return self.run_tests("tests.test_operational_intelligence tests.test_accounting tests.test_inventory")

    def run_integration_tests(self) -> dict:
        """Run integration tests."""
        return self.run_tests("tests.test_api")

    def run_all_tests(self) -> dict:
        """Run all tests."""
        return self.run_tests("tests", verbosity=1)
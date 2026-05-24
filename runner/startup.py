"""Startup module - Backend and frontend startup."""
import subprocess
import time
import socket
import sys
from pathlib import Path


class StartupManager:
    """Manage backend and frontend startup."""

    def __init__(self, backend_dir: Path, frontend_dir: Path):
        self.backend_dir = backend_dir
        self.frontend_dir = frontend_dir
        self.backend_process = None
        self.frontend_process = None

    def check_port(self, port: int) -> bool:
        """Check if port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def check_backend_api_healthy(self) -> bool:
        """Check if backend API is responding."""
        try:
            import requests
            resp = requests.get("http://localhost:8000/api/ops/health/", timeout=5)
            return resp.status_code == 200
        except (ImportError, requests.RequestException, ConnectionError):
            return False

    def start_backend(self, port: int = 8000) -> bool:
        """Start Django backend server."""
        if not self.check_port(port):
            print(f"[X] Port {port} already in use. Backend may be running.")
            return True

        print(f">> Starting backend on port {port}...")
        try:
            self.backend_process = subprocess.Popen(
                [sys.executable, "manage.py", "runserver", str(port)],
                cwd=str(self.backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Wait for backend to be ready
            for _ in range(30):
                time.sleep(1)
                if self.check_backend_api_healthy():
                    print(f"[OK] Backend started on http://localhost:{port}")
                    return True
            print(f"[!] Backend started but health check timed out")
            return True
        except Exception as e:
            print(f"[X] Failed to start backend: {e}")
            return False

    def stop_backend(self):
        """Stop backend server."""
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
            print("STOP Backend stopped")

    def start_frontend(self) -> bool:
        """Start PySide6 frontend."""
        frontend_main = self.frontend_dir / "main.py"
        if not frontend_main.exists():
            frontend_main = self.frontend_dir / "ui" / "main_window.py"
        if not frontend_main.exists():
            print(f"[X] Frontend entry point not found")
            return False

        print(">> Starting frontend...")
        try:
            self.frontend_process = subprocess.Popen(
                [sys.executable, str(frontend_main)],
                cwd=str(self.frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("[OK] Frontend started")
            return True
        except Exception as e:
            print(f"[X] Failed to start frontend: {e}")
            return False

    def stop_frontend(self):
        """Stop frontend."""
        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process.wait()
            print("STOP Frontend stopped")

    def cleanup(self):
        """Stop all processes."""
        self.stop_backend()
        self.stop_frontend()
#!/usr/bin/env python
"""
ERP System Startup Helper
Creates and manages virtual environment
"""
import subprocess
import sys
import os
from pathlib import Path


def setup_venv():
    """Create and activate virtual environment."""
    base_dir = Path(__file__).parent
    venv_dir = base_dir / "venv"

    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])

    # Get pip from venv
    if os.name == "nt":
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"

    # Install requirements
    req_file = base_dir / "backend" / "requirements.txt"
    if req_file.exists():
        print("Installing dependencies...")
        subprocess.run([str(pip_path), "install", "-r", str(req_file)])

    return python_path, pip_path


def run_with_venv(script_path, *args):
    """Run a script using the virtual environment."""
    python_path, _ = setup_venv()
    subprocess.run([str(python_path), script_path, *args])


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "help"

    if action == "setup":
        setup_venv()
        print("Done! Virtual environment ready.")

    elif action == "install":
        setup_venv()
        print("Dependencies installed!")

    elif action == "start":
        python_path, _ = setup_venv()
        subprocess.run([str(python_path), "run_erp.py", "start-full"])

    elif action == "help":
        print("""
ERP Setup Commands:
==================

# First time setup:
python setup.py install

# Start full system:
python setup.py start

# Or use run_erp.py directly (requires manual venv activation):
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate     # Windows
python run_erp.py start-full
""")

    else:
        print(f"Unknown command: {action}")
        print("Run: python setup.py help")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Enterprise UX Certification Pre-Commit Hook
============================================
Runs both the Design System Enforcer and Enterprise UX Certifier
as a single pre-commit step. Exits non-zero if either fails.

Usage:
    python scripts/pre_commit_certifier.py
"""

import sys
import subprocess
from pathlib import Path


FRONTEND_DIR = Path(__file__).parent.parent


def run_enforcer():
    """Run the design system enforcer on staged files."""
    print("=" * 70)
    print("STEP 1/2: DESIGN SYSTEM ENFORCER")
    print("=" * 70)
    result = subprocess.run(
        [sys.executable, str(FRONTEND_DIR / "scripts" / "pre_commit_enforcer.py"), "--staged-only"],
        cwd=FRONTEND_DIR,
    )
    return result.returncode == 0


def run_certifier():
    """Run the enterprise UX certifier as a full scan."""
    print()
    print("=" * 70)
    print("STEP 2/2: ENTERPRISE UX CERTIFIER")
    print("=" * 70)
    result = subprocess.run(
        [sys.executable, str(FRONTEND_DIR / "enterprise_certification" / "run_certifier_cli.py")],
        cwd=FRONTEND_DIR,
    )
    return result.returncode == 0


def main():
    enforcer_ok = run_enforcer()
    certifier_ok = run_certifier()

    print()
    print("=" * 70)
    if enforcer_ok and certifier_ok:
        print("[APPROVED] ALL CHECKS PASSED - COMMIT ALLOWED")
        print("=" * 70)
        return 0
    else:
        print("[BLOCKED] PRE-COMMIT CHECKS FAILED:")
        if not enforcer_ok:
            print("  - Design System Enforcer: VIOLATIONS FOUND")
        if not certifier_ok:
            print("  - Enterprise UX Certifier: NOT PRODUCTION_READY")
        print("=" * 70)
        print("Fix issues above before committing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

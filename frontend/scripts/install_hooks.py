#!/usr/bin/env python3
"""
Git Hooks Installer
===================
Installs pre-commit and pre-push hooks for design system enforcement.

Usage:
    python scripts/install_hooks.py [--local] [--global]
"""

import os
import sys
import stat
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
HOOKS_DIR = FRONTEND_DIR / ".git" / "hooks"
PRE_COMMIT_HOOK = HOOKS_DIR / "pre-commit"
PRE_PUSH_HOOK = HOOKS_DIR / "pre-push"


def create_pre_commit_hook():
    """Create pre-commit hook that runs design system enforcer"""
    content = """#!/bin/bash
# Pre-commit hook for Design System Enforcement
# DO NOT BYPASS - This ensures ZERO design violations in commits

echo "Running Design System Enforcement Check..."
echo ""

# Change to frontend directory
cd "$(git rev-parse --show-toplevel)/frontend"

# Run the enforcer on staged files
python scripts/pre_commit_enforcer.py --staged-only
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "COMMIT BLOCKED: Design System Violations"
    echo "========================================"
    echo ""
    echo "Your commit contains design system violations."
    echo "Please fix them before committing."
    echo ""
    echo "Run 'python scripts/pre_commit_enforcer.py --full-scan' for details."
    exit 1
fi

echo "Design System Check: PASSED"
exit 0
"""
    return content


def create_pre_push_hook():
    """Create pre-push hook that runs full design system check"""
    content = """#!/bin/bash
# Pre-push hook for Design System Enforcement
# DO NOT BYPASS - This ensures ZERO design violations before push

echo "Running Design System Enforcement (Full Check)..."
echo ""

# Change to frontend directory
cd "$(git rev-parse --show-toplevel)/frontend"

# Run full scan on all changed files
python scripts/pre_commit_enforcer.py --full-scan
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "PUSH BLOCKED: Design System Violations"
    echo "========================================"
    echo ""
    echo "Your push contains design system violations."
    echo "Please fix them before pushing."
    exit 1
fi

echo "Design System Full Check: PASSED"
exit 0
"""
    return content


def install_hooks(local: bool = True):
    """Install git hooks"""
    # Ensure hooks directory exists
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create pre-commit hook
    print(f"Installing pre-commit hook to {PRE_COMMIT_HOOK}...")
    with open(PRE_COMMIT_HOOK, 'w') as f:
        f.write(create_pre_commit_hook())
    
    # Make executable
    os.chmod(PRE_COMMIT_HOOK, os.stat(PRE_COMMIT_HOOK).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    # Create pre-push hook
    print(f"Installing pre-push hook to {PRE_PUSH_HOOK}...")
    with open(PRE_PUSH_HOOK, 'w') as f:
        f.write(create_pre_push_hook())
    
    # Make executable
    os.chmod(PRE_PUSH_HOOK, os.stat(PRE_PUSH_HOOK).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    print("\n" + "=" * 60)
    print("Git hooks installed successfully!")
    print("=" * 60)
    print()
    print("The following hooks are now active:")
    print("  - pre-commit:  Runs on 'git commit' (staged files)")
    print("  - pre-push:    Runs on 'git push' (full scan)")
    print()
    print("To bypass (NOT RECOMMENDED):")
    print("  git commit --no-verify  # Skip pre-commit")
    print("  git push --no-verify    # Skip pre-push")
    print()
    print("To uninstall:")
    print("  rm .git/hooks/pre-commit")
    print("  rm .git/hooks/pre-push")


def uninstall_hooks():
    """Remove git hooks"""
    if PRE_COMMIT_HOOK.exists():
        PRE_COMMIT_HOOK.unlink()
        print(f"Removed {PRE_COMMIT_HOOK}")
    
    if PRE_PUSH_HOOK.exists():
        PRE_PUSH_HOOK.unlink()
        print(f"Removed {PRE_PUSH_HOOK}")
    
    print("Git hooks uninstalled.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Git Hooks Installer")
    parser.add_argument("--uninstall", action="store_true", help="Remove installed hooks")
    parser.add_argument("--local", action="store_true", default=True, help="Local repository hooks (default)")
    
    args = parser.parse_args()
    
    if args.uninstall:
        uninstall_hooks()
    else:
        install_hooks(local=args.local)


if __name__ == "__main__":
    main()
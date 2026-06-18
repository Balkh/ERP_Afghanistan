#!/usr/bin/env python
"""Start ERP Afghanistan in curated customer demo mode."""
from runner.orchestrator import ERPRunner


if __name__ == "__main__":
    ERPRunner().start_demo_system()

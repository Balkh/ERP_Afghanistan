#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unified ERP System Runner
=========================
Orchestrates backend, frontend, and testing in one workflow.

Commands:
    start-backend      Start Django backend
    start-frontend     Start PySide6 frontend
    start-full         Start both backend and frontend
    test               Run all tests
    test-backend       Run backend tests only
    test-integration   Run integration tests
    start-demo         Start curated customer demo mode
    status             Show system status
    health             Check system health before startup
    help               Show this help message
"""
import sys
from runner.orchestrator import ERPRunner


def main():
    runner = ERPRunner()
    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    try:
        if command == "start-backend":
            runner.start_backend()
        elif command == "start-frontend":
            runner.start_frontend()
        elif command == "start-full":
            runner.start_full_system()
        elif command == "start-demo":
            runner.start_demo_system()
        elif command == "test":
            result = runner.run_tests()
            print(f"\nSTAT Tests completed in {result['elapsed']}s")
            print(f"Passed: {result['passed']}, Failed: {result['failed_count']}")
        elif command == "test-backend":
            result = runner.run_backend_tests()
            print(f"\nSTAT Backend tests: {result['elapsed']}s - {'PASS' if result['passed'] else 'FAIL'}")
        elif command == "test-integration":
            result = runner.run_integration_tests()
            print(f"\nSTAT Integration tests: {result['elapsed']}s - {'PASS' if result['passed'] else 'FAIL'}")
        elif command == "status":
            status = runner.check_status()
            print("\nSTAT System Status:")
            for k, v in status.items():
                print(f"  {k}: {v}")
        elif command == "health":
            result = runner.run_health_check()
            print("CHECK Running system health check...")
            for name, passed in result["checks"].items():
                print(f"  {'[OK]' if passed else '[X]'} {name}: {'OK' if passed else 'FAILED'}")
        elif command == "help":
            print(__doc__)
        else:
            print(f"Unknown command: {command}")
            print("Run: python run_erp.py help")
    except KeyboardInterrupt:
        print("\nSTOP Shutting down...")
        runner.cleanup()
    except Exception as e:
        print(f"[X] Error: {e}")
        runner.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
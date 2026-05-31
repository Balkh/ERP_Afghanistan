#!/usr/bin/env python3
"""Runtime audit profiler — measures import time, module load, and screen init (headless where possible)."""
from __future__ import annotations

import importlib
import os
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
os.chdir(FRONTEND)
sys.path.insert(0, str(FRONTEND))
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("PHARMACY_ERP_DEVELOPMENT", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def timed_import(module_name: str) -> tuple[float, int | None]:
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        importlib.import_module(module_name)
        ok = True
    except Exception as e:
        ok = False
        print(f"  IMPORT FAIL {module_name}: {e}")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed_ms, peak if ok else None


def profile_startup_imports():
    """Measure cold imports matching main.py → MainWindow chain."""
    chain = [
        "theme.theme_engine",
        "ui.main_window",
        "api.client",
        "security.auth_manager",
        "utils.logger",
        "license.license_validator",
        "security.tamper_detector",
    ]
    results = []
    for mod in chain:
        ms, peak = timed_import(module_name=mod.replace("/", "."))
        results.append((mod, ms, peak or 0))
    return results


def profile_mainwindow_build():
    """QApplication + MainWindow without event loop."""
    from PySide6.QtWidgets import QApplication
    from theme.theme_engine import ThemeEngine
    from api.client import APIClient
    from security.auth_manager import AuthManager
    from license.license_validator import initialize_license_validation

    timings = {}
    tracemalloc.start()
    t0 = time.perf_counter()
    app = QApplication.instance() or QApplication([])
    timings["QApplication"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    ThemeEngine.instance().apply_theme("dark")
    timings["ThemeEngine"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    initialize_license_validation(dev_mode=True)
    timings["License"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    api = APIClient()
    auth = AuthManager(api)
    timings["API+Auth"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    from ui.main_window import MainWindow
    timings["import MainWindow module"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    user = {"username": "dev_admin", "role": "admin", "roles": ["Admin"]}
    auth._user_data = user
    auth._is_authenticated = True
    lv = initialize_license_validation(dev_mode=True)
    window = MainWindow(license_validator=lv, user_data=user, api_client=api, auth_manager=auth)
    timings["MainWindow.__init__"] = (time.perf_counter() - t0) * 1000

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return timings, peak


def profile_intelligence_hub():
    from PySide6.QtWidgets import QApplication
    from api.client import APIClient

    app = QApplication.instance() or QApplication([])
    api = APIClient()
    breakdown = {}

    t0 = time.perf_counter()
    from ui.system.intelligence_hub_screen import IntelligenceHubScreen
    breakdown["import IntelligenceHubScreen"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    screen = IntelligenceHubScreen(api_client=api)
    breakdown["IntelligenceHubScreen.__init__"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    screen._on_screen_shown()
    breakdown["_on_screen_shown (overview refresh)"] = (time.perf_counter() - t0) * 1000

    tabs = [
        (1, "ControlCenterScreen"),
        (2, "WorkflowIntelligenceScreen"),
        (3, "SystemIntegrityScreen"),
        (4, "DriftIntelligenceScreen"),
        (5, "SystemCorrelationScreen"),
    ]
    for idx, label in tabs:
        t0 = time.perf_counter()
        screen._on_tab_changed(idx)
        breakdown[f"tab {idx} {label}"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    screen._on_tab_changed(6)
    breakdown["tab 6 Decisions"] = (time.perf_counter() - t0) * 1000

    return breakdown


def profile_screen_inits():
    from PySide6.QtWidgets import QApplication
    from api.client import APIClient

    app = QApplication.instance() or QApplication([])
    api = APIClient()
    screens = [
        ("inventory", "ui.inventory.product_screen", "ProductScreen"),
        ("sales", "ui.sales.customer_screen", "CustomerScreen"),
        ("accounting", "ui.accounting.chart_of_accounts_screen", "ChartOfAccountsScreen"),
        ("intelligence_hub", "ui.system.intelligence_hub_screen", "IntelligenceHubScreen"),
        ("control_center_tab", "ui.system.control_center_screen", "ControlCenterScreen"),
    ]
    results = []
    for name, mod, cls_name in screens:
        t0 = time.perf_counter()
        try:
            m = importlib.import_module(mod)
            cls = getattr(m, cls_name)
            if cls_name == "ChartOfAccountsScreen":
                w = cls()
            else:
                w = cls(api_client=api)
            ms = (time.perf_counter() - t0) * 1000
            results.append((name, ms, "ok"))
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            results.append((name, ms, str(e)[:80]))
    return results


def backend_simulation_import_cost():
    t0 = time.perf_counter()
    try:
        import simulation.control_center.orchestrator.control_center_engine  # noqa: F401
        ok = True
    except Exception as e:
        ok = False
        err = str(e)
    ms = (time.perf_counter() - t0) * 1000
    return ms, ok, err if not ok else ""


def count_event_bus_subscribers():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from core.events import EnterpriseEventBus
    from core.events.handlers import register_all_handlers
    register_all_handlers()
    subs = EnterpriseEventBus._subscribers
    total_handlers = sum(len(v) for v in subs.values())
    return len(subs), total_handlers, list(subs.keys())


def main():
    print("=" * 60)
    print("PHASE 1 — Startup import chain")
    print("=" * 60)
    for mod, ms, peak in sorted(profile_startup_imports(), key=lambda x: -x[1])[:20]:
        print(f"  {ms:8.1f} ms  peak={peak/1024/1024:.2f}MB  {mod}")

    print("\n" + "=" * 60)
    print("PHASE 1b — MainWindow build (offscreen Qt)")
    print("=" * 60)
    timings, peak = profile_mainwindow_build()
    for k, v in sorted(timings.items(), key=lambda x: -x[1]):
        print(f"  {v:8.1f} ms  {k}")
    print(f"  Peak traced memory after MainWindow: {peak/1024/1024:.1f} MB")

    print("\n" + "=" * 60)
    print("PHASE 2 — Intelligence Hub breakdown")
    print("=" * 60)
    for k, v in sorted(profile_intelligence_hub().items(), key=lambda x: -x[1]):
        print(f"  {v:8.1f} ms  {k}")

    print("\n" + "=" * 60)
    print("PHASE 6 — Screen init comparison")
    print("=" * 60)
    for name, ms, status in sorted(profile_screen_inits(), key=lambda x: -x[1]):
        print(f"  {ms:8.1f} ms  {name:20s}  {status}")

    print("\n" + "=" * 60)
    print("PHASE 3 — Simulation import cost (backend)")
    print("=" * 60)
    ms, ok, err = backend_simulation_import_cost()
    print(f"  simulation.control_center_engine import: {ms:.1f} ms  ok={ok} {err}")

    print("\n" + "=" * 60)
    print("PHASE 5 — Event bus (Django)")
    print("=" * 60)
    try:
        n_types, n_handlers, keys = count_event_bus_subscribers()
        print(f"  Event types: {n_types}, handlers: {n_handlers}")
        for k in keys:
            print(f"    - {k}")
    except Exception as e:
        print(f"  SKIP: {e}")


if __name__ == "__main__":
    main()

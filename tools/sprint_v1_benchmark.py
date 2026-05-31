#!/usr/bin/env python3
"""Performance Sprint V1 — before/after style benchmark (run from frontend/)."""
from __future__ import annotations

import importlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")
os.chdir(FRONTEND)
sys.path.insert(0, FRONTEND)
os.environ["PHARMACY_ERP_DEVELOPMENT"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def ms(t0):
    return (time.perf_counter() - t0) * 1000


def bench_startup():
    from PySide6.QtWidgets import QApplication
    from theme.theme_engine import ThemeEngine
    from api.client import APIClient
    from security.auth_manager import AuthManager
    from license.license_validator import initialize_license_validation

    t0 = time.perf_counter()
    app = QApplication.instance() or QApplication([])
    ThemeEngine.instance().apply_theme("dark")
    api = APIClient()
    auth = AuthManager(api)
    auth._user_data = {"username": "dev", "roles": ["Admin"]}
    auth._is_authenticated = True
    lv = initialize_license_validation(dev_mode=True)

    t_import = time.perf_counter()
    importlib.import_module("ui.main_window")
    import_main = ms(t_import)

    t_build = time.perf_counter()
    from ui.main_window import MainWindow
    MainWindow(license_validator=lv, user_data=auth._user_data, api_client=api, auth_manager=auth)
    build_ms = ms(t_build)
    return {"import_main_window_ms": import_main, "mainwindow_init_ms": build_ms, "total_ms": ms(t0)}


def bench_hub_tabs():
    from PySide6.QtWidgets import QApplication
    from api.client import APIClient
    from ui.system.intelligence_hub_screen import IntelligenceHubScreen

    QApplication.instance() or QApplication([])
    api = APIClient()
    hub = IntelligenceHubScreen(api_client=api)
    results = {}

    t0 = time.perf_counter()
    hub._on_screen_shown()
    results["overview_ms"] = ms(t0)

    for idx, name in [(1, "workflow"), (2, "workflow_tab2"), (4, "drift"), (5, "correlation")]:
        t0 = time.perf_counter()
        hub._on_tab_changed(idx)
        # Allow worker threads brief time without blocking full 30s
        deadline = time.perf_counter() + 8.0
        app = QApplication.instance()
        while time.perf_counter() < deadline:
            app.processEvents()
            time.sleep(0.05)
        results[f"tab_{idx}_{name}_ui_return_ms"] = ms(t0)

    return results


def bench_fail_fast():
    from api.client import APIClient
    client = APIClient()
    t0 = time.perf_counter()
    client.get("/api/workflows/instances/", background=True, retries=3)
    return ms(t0)


if __name__ == "__main__":
    print("=== Sprint V1 Benchmark ===")
    for k, v in bench_startup().items():
        print(f"  {k}: {v:.1f}")
    print("--- Hub tabs (UI return after 8s poll) ---")
    for k, v in bench_hub_tabs().items():
        print(f"  {k}: {v:.1f}")
    print(f"--- Fail-fast workflow GET (retries=3) ---")
    print(f"  elapsed_ms: {bench_fail_fast():.1f}")

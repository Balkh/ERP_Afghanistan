#!/usr/bin/env python3
"""
Sprint 2.5 — Post-stabilization validation (evidence only, no code changes).
Outputs: tools/sprint_2_5_results.json
Run: python tools/sprint_2_5_validation_runner.py
"""
from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
RESULTS_PATH = os.path.join(ROOT, "tools", "sprint_2_5_results.json")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("SPRINT_25_API_ITERATIONS", "5")
os.environ.setdefault("SPRINT_25_FRONTEND_RUNS", "5")
sys.path.insert(0, BACKEND)

import logging
logging.disable(logging.WARNING)


def _stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"count": 0, "min_ms": None, "max_ms": None, "avg_ms": None, "p95_ms": None}
    s = sorted(values)
    p95_idx = max(0, int(len(s) * 0.95) - 1)
    return {
        "count": len(s),
        "min_ms": round(min(s), 2),
        "max_ms": round(max(s), 2),
        "avg_ms": round(statistics.mean(s), 2),
        "p95_ms": round(s[p95_idx], 2),
        "samples_ms": [round(v, 2) for v in s],
    }


def _django_setup():
    import django
    django.setup()


def collect_environment() -> Dict[str, Any]:
    _django_setup()
    import django
    from django.conf import settings
    from django.db import connection

    env: Dict[str, Any] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor() or platform.machine(),
        "python_version": platform.python_version(),
        "django_version": django.get_version(),
    }

    try:
        import psutil
        env["cpu_logical"] = psutil.cpu_count(logical=True)
        env["cpu_physical"] = psutil.cpu_count(logical=False)
        mem = psutil.virtual_memory()
        env["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)
        env["ram_available_gb"] = round(mem.available / (1024 ** 3), 2)
        disk = psutil.disk_usage(ROOT[:2] if os.name == "nt" else "/")
        env["storage_total_gb"] = round(disk.total / (1024 ** 3), 2)
        env["storage_free_gb"] = round(disk.free / (1024 ** 3), 2)
    except ImportError:
        env["psutil"] = "NOT INSTALLED"

    try:
        from PySide6.QtCore import qVersion
        env["qt_version"] = qVersion()
    except Exception as e:
        env["qt_version"] = f"NOT VERIFIED ({e})"

    db = settings.DATABASES.get("default", {})
    env["database_engine"] = db.get("ENGINE", "unknown")
    env["database_name"] = db.get("NAME", "")

    counts: Dict[str, Any] = {}
    try:
        from inventory.models import Product
        from sales.models import Customer, SalesInvoice, CustomerPayment
        from accounting.models import JournalEntry
        from workflows.models import WorkflowInstance

        counts = {
            "products": Product.objects.count(),
            "customers": Customer.objects.count(),
            "invoices": SalesInvoice.objects.count(),
            "payments": CustomerPayment.objects.count(),
            "journal_entries": JournalEntry.objects.count(),
            "workflow_instances": WorkflowInstance.objects.count(),
        }
    except Exception as e:
        counts["error"] = str(e)

    env["entity_counts"] = counts

    try:
        with connection.cursor() as cur:
            if "postgresql" in env["database_engine"]:
                cur.execute("SELECT pg_database_size(current_database())")
                env["database_size_bytes"] = cur.fetchone()[0]
                cur.execute(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                env["database_size_pretty"] = cur.fetchone()[0]
            else:
                env["database_size_bytes"] = "NOT VERIFIED (non-PostgreSQL)"
    except Exception as e:
        env["database_size_error"] = str(e)

    return env


def _get_test_user_and_company():
    from django.contrib.auth import get_user_model
    from core.multitenant.context import TenantContext

    User = get_user_model()
    user = User.objects.filter(is_active=True).first()
    if not user:
        raise RuntimeError("No active user for API validation")

    company_id = None
    if getattr(user, "company_id", None):
        company_id = str(user.company_id)
    else:
        try:
            from companies.models import Company
            first = Company.objects.filter(is_active=True).first()
            if first:
                company_id = str(first.id)
        except Exception:
            pass

    if company_id:
        TenantContext.set_company_id(company_id)
    return user, company_id


def _drf_client():
    from rest_framework.test import APIClient

    user, company_id = _get_test_user_and_company()
    client = APIClient()
    client.force_authenticate(user=user)
    headers = {}
    if company_id:
        headers["HTTP_X_COMPANY_ID"] = company_id
    return client, headers, user


def _api_request(method: str, path: str, n: int | None = None) -> Dict[str, Any]:
    if n is None:
        n = int(os.environ.get("SPRINT_25_API_ITERATIONS", "5"))
    client, headers, _user = _drf_client()
    # Warm-up (excluded from stats)
    if method == "GET":
        client.get(path, **headers)
    times: List[float] = []
    statuses: List[int] = []
    sizes: List[int] = []
    errors = 0

    for _ in range(n):
        t0 = time.perf_counter()
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)
        statuses.append(resp.status_code)
        content = resp.content or b""
        sizes.append(len(content))
        if resp.status_code >= 400:
            errors += 1

    status_dist: Dict[str, int] = {}
    for s in statuses:
        status_dist[str(s)] = status_dist.get(str(s), 0) + 1

    return {
        "path": path,
        "method": method,
        "iterations": n,
        "timing_ms": _stats(times),
        "payload_bytes": _stats([float(x) for x in sizes]),
        "error_count": errors,
        "error_rate": round(errors / n, 4) if n else None,
        "http_status_distribution": status_dist,
    }


def validate_hub_bundle(user) -> Dict[str, Any]:
    import json as _json
    from rest_framework.test import APIClient
    from django.test import RequestFactory
    from core.operations.hub_bff import intelligence_hub_bundle
    from django.db import connection
    from core.multitenant.context import TenantContext

    _, company_id = _get_test_user_and_company()
    if company_id:
        TenantContext.set_company_id(company_id)

    expected_keys = [
        "health", "stats", "intelligence", "signals", "jobs",
        "financial", "inventory", "operations",
        "workflow_instances", "workflows_pending", "correlation_sources",
    ]
    client = APIClient()
    client.force_authenticate(user=user)
    hdrs = {"HTTP_X_COMPANY_ID": company_id} if company_id else {}

    view_times: List[float] = []
    db_times: List[float] = []
    ser_times: List[float] = []
    payload_sizes: List[int] = []
    missing_keys_runs: List[List[str]] = []

    client.get("/api/control-center/hub-bundle/", **hdrs)  # warm-up
    for _ in range(5):
        t0 = time.perf_counter()
        resp = client.get("/api/control-center/hub-bundle/", **hdrs)
        total_ms = (time.perf_counter() - t0) * 1000
        view_times.append(total_ms)
        payload_sizes.append(len(resp.content or b""))

        if resp.status_code != 200:
            missing_keys_runs.append([f"HTTP_{resp.status_code}"])
            continue
        try:
            body = resp.json()
            data = body.get("data", body) if isinstance(body, dict) else body
            missing = [k for k in expected_keys if k not in (data or {})]
            missing_keys_runs.append(missing)
        except Exception:
            missing_keys_runs.append(["PARSE_ERROR"])

    factory = RequestFactory()
    for _ in range(5):
        req = factory.get("/api/control-center/hub-bundle/")
        req.user = user
        t0 = time.perf_counter()
        with connection.execute_wrapper(_QueryTimer(db_times)):
            resp = intelligence_hub_bundle(req)
        ser_times.append((time.perf_counter() - t0) * 1000)
        if hasattr(resp, "data"):
            payload_sizes.append(len(_json.dumps(resp.data, default=str)))

    all_missing = set()
    for m in missing_keys_runs:
        all_missing.update(m)

    return {
        "http_timing_ms": _stats(view_times),
        "payload_bytes": _stats([float(x) for x in payload_sizes]),
        "expected_keys": expected_keys,
        "missing_keys_observed": sorted(all_missing),
        "keys_valid": len(all_missing) == 0,
        "view_function_timing_ms": _stats(ser_times) if ser_times else "NOT VERIFIED",
        "db_time_accumulated_ms": _stats(db_times) if db_times else "NOT VERIFIED",
        "duplicate_data_check": _check_bundle_duplicates(user),
    }


class _QueryTimer:
    def __init__(self, bucket: List[float]):
        self.bucket = bucket

    def __call__(self, execute, sql, params, many, context):
        t0 = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.bucket.append((time.perf_counter() - t0) * 1000)


def _check_bundle_duplicates(user) -> Dict[str, Any]:
    from django.test import RequestFactory
    from core.operations.hub_bff import intelligence_hub_bundle

    factory = RequestFactory()
    req = factory.get("/api/control-center/hub-bundle/")
    req.user = user
    resp = intelligence_hub_bundle(req)
    if resp.status_code != 200:
        return {"verified": False, "reason": f"status_{resp.status_code}"}
    data = resp.data
    wf_ids = {str(x.get("id")) for x in (data.get("workflow_instances") or [])}
    corr_wf = data.get("correlation_sources", {}).get("workflows", [])
    corr_ids = {str(x.get("id")) for x in corr_wf}
    overlap = wf_ids & corr_ids if wf_ids and corr_ids else set()
    return {
        "workflow_instances_count": len(data.get("workflow_instances") or []),
        "correlation_workflows_count": len(corr_wf),
        "id_overlap_count": len(overlap),
        "note": "Overlap expected (correlation embeds workflow rows); flag if counts diverge wildly",
    }


def explain_queryset(label: str, qs, limit: int = 50) -> Dict[str, Any]:
    from django.db import connection

    qs = qs[:limit]
    try:
        sql, params = qs.query.sql_with_params()
        params = tuple("" if p is None else str(p) for p in params)
    except Exception as e:
        return {"label": label, "error": str(e)}

    result: Dict[str, Any] = {"label": label, "sql_preview": sql[:500]}
    engine = connection.settings_dict["ENGINE"]
    try:
        with connection.cursor() as cur:
            if "postgresql" in engine:
                cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params)
                plan = cur.fetchone()[0]
                if isinstance(plan, str):
                    plan = json.loads(plan)
                root = plan[0] if isinstance(plan, list) else plan
                plan_node = root.get("Plan", root)
                result["execution_time_ms"] = root.get("Execution Time")
                result["planning_time_ms"] = root.get("Planning Time")
                result["total_cost"] = plan_node.get("Total Cost")
                result["plan_rows"] = plan_node.get("Plan Rows")
                result["node_type"] = plan_node.get("Node Type")
                result["index_scan"] = _find_index_usage(plan_node)
                result["seq_scan"] = _find_seq_scan(plan_node)
                result["full_plan_json"] = plan
            elif "sqlite" in engine:
                cur.execute(f"EXPLAIN QUERY PLAN {sql}", params)
                rows = cur.fetchall()
                result["explain_query_plan"] = [list(r) for r in rows]
                result["index_scan"] = [
                    r[3] for r in rows if len(r) > 3 and "USING INDEX" in str(r[3]).upper()
                ]
                result["seq_scan"] = any("SCAN" in str(r) for r in rows)
            else:
                cur.execute(f"EXPLAIN {sql}", params)
                result["explain_text"] = "\n".join(r[0] for r in cur.fetchall())
    except Exception as e:
        result["explain_error"] = str(e)

    t0 = time.perf_counter()
    list(qs)
    result["orm_fetch_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return result


def _find_index_usage(node: dict) -> List[str]:
    found = []
    if "Index" in node.get("Node Type", ""):
        found.append(node.get("Index Name", node.get("Relation Name", "?")))
    for child in node.get("Plans", []) or []:
        found.extend(_find_index_usage(child))
    return found


def _find_seq_scan(node: dict) -> bool:
    if node.get("Node Type") == "Seq Scan":
        return True
    return any(_find_seq_scan(c) for c in (node.get("Plans", []) or []))


def database_validation() -> Dict[str, Any]:
    _django_setup()
    from workflows.models import WorkflowInstance
    from sales.models import SalesInvoice
    from accounting.models import JournalEntry

    wf_qs = WorkflowInstance.objects.filter(is_active=True).select_related(
        "pending_approver", "created_by", "company"
    ).order_by("-created_at")
    inv_qs = SalesInvoice.objects.filter(is_active=True).select_related(
        "customer", "company"
    ).order_by("-created_at")
    je_qs = JournalEntry.objects.filter(is_active=True).select_related(
        "created_by", "company"
    ).prefetch_related("lines", "lines__account").order_by("-entry_date")

    return {
        "workflow_list": explain_queryset("workflow_list", wf_qs),
        "invoice_list": explain_queryset("invoice_list", inv_qs),
        "journal_list": explain_queryset("journal_list", je_qs),
    }


def api_validation() -> Dict[str, Any]:
    _django_setup()
    _user, _cid = _get_test_user_and_company()
    user = _user
    endpoints = [
        ("GET", "/api/workflows/instances/"),
        ("GET", "/api/control-center/hub-bundle/"),
        ("GET", "/api/accounting/journal-entries/?limit=50"),
        ("GET", "/api/sales/invoices/?limit=50"),
    ]
    results = {}
    for method, path in endpoints:
        key = path.split("/api/")[-1].rstrip("/").replace("/", "_")
        results[key] = _api_request(method, path)
    results["hub_bundle_detail"] = validate_hub_bundle(user)
    return results


def _ensure_frontend_path():
    os.environ["PHARMACY_ERP_DEVELOPMENT"] = "1"
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if FRONTEND not in sys.path:
        sys.path.insert(0, FRONTEND)
    os.chdir(FRONTEND)


def frontend_startup_benchmark(runs: int = 5) -> Dict[str, Any]:
    _ensure_frontend_path()

    phases = {
        "cold_app_to_theme_ms": [],
        "login_screen_visible_ms": [],
        "mainwindow_ready_ms": [],
        "dashboard_first_paint_ms": [],
    }

    for _ in range(runs):
        from PySide6.QtWidgets import QApplication
        import importlib

        t0 = time.perf_counter()
        app = QApplication.instance() or QApplication([])
        from theme.theme_engine import ThemeEngine
        ThemeEngine.instance().apply_theme("dark")
        phases["cold_app_to_theme_ms"].append((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        importlib.import_module("ui.auth.login_screen")
        from ui.auth.login_screen import LoginDialog
        lw = LoginDialog()
        lw.show()
        app.processEvents()
        phases["login_screen_visible_ms"].append((time.perf_counter() - t1) * 1000)
        lw.close()
        lw.deleteLater()

        t2 = time.perf_counter()
        from api.client import APIClient
        from security.auth_manager import AuthManager
        from license.license_validator import initialize_license_validation
        api = APIClient()
        auth = AuthManager(api)
        auth._user_data = {"username": "bench", "roles": ["Admin"]}
        auth._is_authenticated = True
        lv = initialize_license_validation(dev_mode=True)
        from ui.main_window import MainWindow
        mw = MainWindow(
            license_validator=lv,
            user_data=auth._user_data,
            api_client=api,
            auth_manager=auth,
        )
        mw.show()
        app.processEvents()
        phases["mainwindow_ready_ms"].append((time.perf_counter() - t2) * 1000)

        t3 = time.perf_counter()
        mw.change_page(0)
        app.processEvents()
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)
        phases["dashboard_first_paint_ms"].append((time.perf_counter() - t3) * 1000)
        mw.close()
        mw.deleteLater()

    return {k: _stats(v) for k, v in phases.items()}


def _wait_first_data(app, screen, signal_name: str, timeout_s: float = 30.0) -> Optional[float]:
    from PySide6.QtCore import QEventLoop, QTimer, Signal

    loop = QEventLoop()
    t0 = time.perf_counter()
    got = {"done": False}

    sig = getattr(screen, signal_name, None)
    thread = getattr(screen, "_fetch_thread", None)
    if thread and hasattr(thread, signal_name):
        sig = getattr(thread, signal_name)

    if sig is None:
        return None

    def on_data(*_args):
        if not got["done"]:
            got["done"] = True
            got["ms"] = (time.perf_counter() - t0) * 1000
            loop.quit()

    try:
        sig.connect(on_data)
    except Exception:
        return None

    QTimer.singleShot(int(timeout_s * 1000), loop.quit)
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline and not got["done"]:
        app.processEvents()
        time.sleep(0.02)
    try:
        sig.disconnect(on_data)
    except Exception:
        pass
    return got.get("ms")


def intelligence_hub_benchmark(runs: int = 5) -> Dict[str, Any]:
    _ensure_frontend_path()

    from PySide6.QtWidgets import QApplication
    from api.client import APIClient
    from ui.system.intelligence_hub_screen import IntelligenceHubScreen

    app = QApplication.instance() or QApplication([])
    api = APIClient()
    backend_reachable = False
    try:
        import requests
        r = requests.get("http://localhost:8000/api/health/", timeout=2)
        backend_reachable = r.status_code < 500
    except Exception:
        backend_reachable = False

    metrics: Dict[str, List[float]] = {
        "overview_visible_ms": [],
        "overview_data_ms": [],
        "workflow_visible_ms": [],
        "workflow_first_data_ms": [],
        "workflow_complete_ms": [],
        "correlation_visible_ms": [],
        "correlation_first_data_ms": [],
        "correlation_complete_ms": [],
        "control_center_visible_ms": [],
        "control_center_first_data_ms": [],
        "control_center_complete_ms": [],
    }
    integrated_note = (
        "live_backend" if backend_reachable else "NOT VERIFIED — localhost:8000 unreachable"
    )

    for _ in range(runs):
        hub = IntelligenceHubScreen(api_client=api)

        t0 = time.perf_counter()
        hub.show()
        app.processEvents()
        metrics["overview_visible_ms"].append((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        hub._on_screen_shown()
        app.processEvents()
        for _ in range(30):
            app.processEvents()
            time.sleep(0.02)
        metrics["overview_data_ms"].append((time.perf_counter() - t1) * 1000)

        # Control Center tab = 1
        t0 = time.perf_counter()
        hub._on_tab_changed(1)
        app.processEvents()
        metrics["control_center_visible_ms"].append((time.perf_counter() - t0) * 1000)
        cc = hub.tab_instances[1].get("instance")
        if cc and getattr(cc, "_fetch_thread", None):
            fd = _wait_first_data(app, cc._fetch_thread, "data_received", 30.0)
            if fd is not None:
                metrics["control_center_first_data_ms"].append(fd)
            t_complete = time.perf_counter()
            for _ in range(50):
                app.processEvents()
                if cc and not getattr(cc, "_is_fetching", True):
                    break
                time.sleep(0.05)
            metrics["control_center_complete_ms"].append((time.perf_counter() - t0) * 1000)

        hub._teardown_tab(1)

        # Workflow tab = 2
        t0 = time.perf_counter()
        hub._on_tab_changed(2)
        app.processEvents()
        metrics["workflow_visible_ms"].append((time.perf_counter() - t0) * 1000)
        wf = hub.tab_instances[2].get("instance")
        if wf:
            fd = _wait_first_data(app, wf, "data_received", 30.0)
            if fd is not None:
                metrics["workflow_first_data_ms"].append(fd)
            for _ in range(50):
                app.processEvents()
                time.sleep(0.05)
            metrics["workflow_complete_ms"].append((time.perf_counter() - t0) * 1000)
        hub._teardown_tab(2)

        # Correlation tab = 5
        t0 = time.perf_counter()
        hub._on_tab_changed(5)
        app.processEvents()
        metrics["correlation_visible_ms"].append((time.perf_counter() - t0) * 1000)
        corr = hub.tab_instances[5].get("instance")
        if corr and corr._fetch_thread:
            fd = _wait_first_data(app, corr._fetch_thread, "data_received", 30.0)
            if fd is not None:
                metrics["correlation_first_data_ms"].append(fd)
            for _ in range(50):
                app.processEvents()
                time.sleep(0.05)
            metrics["correlation_complete_ms"].append((time.perf_counter() - t0) * 1000)
        hub._teardown_tab(5)
        hub.deleteLater()

    out = {k: _stats(v) if v else {"note": "NOT VERIFIED"} for k, v in metrics.items()}
    out["integration_mode"] = integrated_note
    return out


def memory_stability_test(switches: int = 100) -> Dict[str, Any]:
    _ensure_frontend_path()

    try:
        import psutil
        proc = psutil.Process(os.getpid())
    except ImportError:
        return {"error": "NOT VERIFIED — psutil required"}

    from PySide6.QtWidgets import QApplication
    from api.client import APIClient
    from ui.system.intelligence_hub_screen import IntelligenceHubScreen

    app = QApplication.instance() or QApplication([])
    api = APIClient()
    hub = IntelligenceHubScreen(api_client=api)
    hub.show()
    app.processEvents()

    initial_rss = proc.memory_info().rss / (1024 * 1024)
    peak_rss = initial_rss
    thread_samples = []

    cycle = [0, 2, 5, 1]
    for i in range(switches):
        idx = cycle[i % len(cycle)]
        hub._on_tab_changed(idx)
        for _ in range(5):
            app.processEvents()
            time.sleep(0.005)
        if idx in (1, 2, 5):
            hub._teardown_tab(idx)
        rss = proc.memory_info().rss / (1024 * 1024)
        peak_rss = max(peak_rss, rss)
        thread_samples.append(proc.num_threads())

    for _ in range(10):
        app.processEvents()
        time.sleep(0.05)

    final_rss = proc.memory_info().rss / (1024 * 1024)
    growth_mb = final_rss - initial_rss

    return {
        "switches": switches,
        "initial_rss_mb": round(initial_rss, 2),
        "peak_rss_mb": round(peak_rss, 2),
        "final_rss_mb": round(final_rss, 2),
        "growth_mb": round(growth_mb, 2),
        "thread_count_initial": thread_samples[0] if thread_samples else None,
        "thread_count_final": thread_samples[-1] if thread_samples else None,
        "thread_count_max": max(thread_samples) if thread_samples else None,
        "leak_suspected": growth_mb > 50,
    }


def tab_teardown_validation() -> Dict[str, Any]:
    _ensure_frontend_path()

    from PySide6.QtWidgets import QApplication, QWidget
    from api.client import APIClient
    from ui.system.intelligence_hub_screen import IntelligenceHubScreen
    from ui.system.control_center_screen import ControlCenterScreen

    app = QApplication.instance() or QApplication([])
    api = APIClient()
    hub = IntelligenceHubScreen(api_client=api)

    hub._on_tab_changed(1)
    app.processEvents()
    inst = hub.tab_instances[1]["instance"]
    cc = inst
    thread_before = getattr(cc, "_fetch_thread", None)
    thread_running_before = thread_before.isRunning() if thread_before else False

    hub._teardown_tab(1)
    app.processEvents()
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)

    instance_after = hub.tab_instances[1]["instance"]
    widget = hub.tabs.widget(1)
    widget_type = type(widget).__name__ if widget else None
    thread_after_running = (
        thread_before.isRunning() if thread_before else False
    )

    # Second load — duplicate check
    hub._on_tab_changed(1)
    app.processEvents()
    inst2 = hub.tab_instances[1]["instance"]
    duplicate_new_instance = inst2 is not None and inst2 is not inst

    checks = {
        "instance_cleared": instance_after is None,
        "placeholder_widget": widget_type == "QWidget",
        "not_control_center_widget": not isinstance(widget, ControlCenterScreen),
        "thread_stopped_after_teardown": not thread_after_running,
        "new_instance_on_reload": duplicate_new_instance,
    }

    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "thread_running_before_teardown": thread_running_before,
        "widget_type_after_teardown": widget_type,
    }


def regression_pytest() -> Dict[str, Any]:
    tests = [
        "tests/test_governance.py",
        "tests/test_restore.py",
        "tests/test_accounting_model.py",
        "security/tests/",
    ]
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=no", "-x"]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=600,
    )
    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "elapsed_s": elapsed,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
        "passed": proc.returncode == 0,
    }


def _save_partial(results: Dict[str, Any]):
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=["all", "env", "api", "db", "frontend", "hub", "memory", "tab", "regression"],
        default="all",
    )
    args = parser.parse_args()

    runs = int(os.environ.get("SPRINT_25_FRONTEND_RUNS", "5"))
    results: Dict[str, Any] = {"generated_at_utc": datetime.now(timezone.utc).isoformat()}
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    phases = (
        ["env", "api", "db", "frontend", "hub", "memory", "tab", "regression"]
        if args.phase == "all"
        else [args.phase]
    )

    for phase in phases:
        print(f"[phase:{phase}] ...")
        if phase == "env":
            results["environment"] = collect_environment()
        elif phase == "api":
            results["api"] = api_validation()
        elif phase == "db":
            results["database"] = database_validation()
        elif phase == "frontend":
            try:
                results["frontend_startup"] = frontend_startup_benchmark(runs)
            except Exception as e:
                results["frontend_startup"] = {"error": str(e), "status": "NOT VERIFIED"}
        elif phase == "hub":
            try:
                results["intelligence_hub"] = intelligence_hub_benchmark(runs)
            except Exception as e:
                results["intelligence_hub"] = {"error": str(e), "status": "NOT VERIFIED"}
        elif phase == "memory":
            try:
                results["memory"] = memory_stability_test(100)
            except Exception as e:
                results["memory"] = {"error": str(e), "status": "NOT VERIFIED"}
        elif phase == "tab":
            try:
                results["tab_teardown"] = tab_teardown_validation()
            except Exception as e:
                results["tab_teardown"] = {"error": str(e), "status": "NOT VERIFIED"}
        elif phase == "regression":
            try:
                results["regression"] = regression_pytest()
            except Exception as e:
                results["regression"] = {"error": str(e), "status": "NOT VERIFIED"}
        _save_partial(results)

    print(f"Wrote {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    main()

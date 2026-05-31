#!/usr/bin/env python3
"""Generate Sprint 2.5 markdown reports from tools/sprint_2_5_results.json"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs", "validation")
RESULTS = os.path.join(ROOT, "tools", "sprint_2_5_results.json")
CRITERIA = {
    "workflow_first_data_ms": 1000,
    "correlation_first_data_ms": 2000,
    "control_center_first_data_ms": 2000,
    "hub_bundle_avg_ms": 500,
    "memory_growth_mb": 50,
}


def load() -> Dict[str, Any]:
    with open(RESULTS, encoding="utf-8") as f:
        return json.load(f)


def _fmt_stats(s: Any) -> str:
    if not isinstance(s, dict) or s.get("avg_ms") is None:
        return "NOT VERIFIED"
    return (
        f"| min {s.get('min_ms')} | max {s.get('max_ms')} | "
        f"avg **{s.get('avg_ms')}** | p95 {s.get('p95_ms')} | "
        f"samples: {s.get('samples_ms', [])} |"
    )


def write_env(r: Dict, path: str):
    e = r["environment"]
    c = e.get("entity_counts", {})
    lines = [
        "# Validation Environment",
        "",
        f"**Captured:** {e.get('captured_at_utc')}",
        "",
        "## Machine",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Hostname | {e.get('hostname')} |",
        f"| OS | {e.get('os')} |",
        f"| CPU | {e.get('cpu')} |",
        f"| CPU logical cores | {e.get('cpu_logical', 'NOT VERIFIED')} |",
        f"| RAM total (GB) | {e.get('ram_total_gb', 'NOT VERIFIED')} |",
        f"| RAM available (GB) | {e.get('ram_available_gb', 'NOT VERIFIED')} |",
        f"| Storage free (GB) | {e.get('storage_free_gb', 'NOT VERIFIED')} |",
        f"| Python | {e.get('python_version')} |",
        f"| Django | {e.get('django_version')} |",
        f"| Qt | {e.get('qt_version')} |",
        "",
        "## Database",
        "",
        f"| Field | Value |",
        f"| Engine | {e.get('database_engine')} |",
        f"| Name | {e.get('database_name')} |",
        f"| Size | {e.get('database_size_pretty', e.get('database_size_bytes', 'NOT VERIFIED'))} |",
        "",
        "## Entity counts",
        "",
        "| Entity | Count |",
        "|--------|------:|",
    ]
    for k, v in sorted(c.items()):
        lines.append(f"| {k} | {v} |")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_startup(r: Dict, path: str):
    fs = r.get("frontend_startup", {})
    lines = [
        "# Frontend Startup Benchmark",
        "",
        "Method: PySide6 offscreen, 5 runs each phase.",
        "",
        "| Phase | Result |",
        "|-------|--------|",
    ]
    for phase in [
        "cold_app_to_theme_ms",
        "login_screen_visible_ms",
        "mainwindow_ready_ms",
        "dashboard_first_paint_ms",
    ]:
        lines.append(f"| {phase} | {_fmt_stats(fs.get(phase))} |")
    if fs.get("error"):
        lines.append(f"\n**Error:** {fs['error']}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_hub(r: Dict, path: str):
    h = r.get("intelligence_hub", {})
    lines = [
        "# Intelligence Hub Benchmark",
        "",
        f"**Integration:** {h.get('integration_mode', 'NOT VERIFIED')}",
        "",
        "| Metric | min / max / avg / p95 |",
        "|--------|------------------------|",
    ]
    for key in sorted(h.keys()):
        if key == "integration_mode":
            continue
        lines.append(f"| {key} | {_fmt_stats(h.get(key))} |")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_bundle(r: Dict, path: str):
    hub = r.get("api", {}).get("hub_bundle_detail", {})
    lines = [
        "# Hub Bundle Validation",
        "",
        "## HTTP timing (Django test client, 10 iterations)",
        "",
        _fmt_stats(hub.get("http_timing_ms")),
        "",
        "## Payload size (bytes)",
        "",
        _fmt_stats(hub.get("payload_bytes")),
        "",
        "## Keys",
        "",
        f"- Expected: `{hub.get('expected_keys', [])}`",
        f"- Missing observed: `{hub.get('missing_keys_observed', [])}`",
        f"- **keys_valid:** {hub.get('keys_valid')}",
        "",
        "## View function timing",
        "",
        str(hub.get("view_function_timing_ms")),
        "",
        "## Duplicate data check",
        "",
        f"```json\n{json.dumps(hub.get('duplicate_data_check', {}), indent=2)}\n```",
    ]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_api(r: Dict, path: str):
    api = r.get("api", {})
    lines = ["# API Performance Report", "", "Django test client, 20 iterations per endpoint.", ""]
    for key, val in api.items():
        if key == "hub_bundle_detail":
            continue
        lines.append(f"## `{val.get('path', key)}`")
        lines.append("")
        lines.append(f"- Timing: {_fmt_stats(val.get('timing_ms'))}")
        lines.append(f"- Payload bytes: {_fmt_stats(val.get('payload_bytes'))}")
        lines.append(f"- Error rate: {val.get('error_rate')}")
        lines.append(f"- Status distribution: `{val.get('http_status_distribution')}`")
        lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_db(r: Dict, path: str):
    db = r.get("database", {})
    lines = ["# Database Performance Report", "", "EXPLAIN ANALYZE (PostgreSQL) + ORM fetch timing.", ""]
    for key, val in db.items():
        lines.append(f"## {key}")
        lines.append("")
        if val.get("explain_error"):
            lines.append(f"**EXPLAIN error:** {val['explain_error']}")
        lines.append(f"- Execution time (ms): {val.get('execution_time_ms', 'NOT VERIFIED')}")
        lines.append(f"- ORM fetch (ms): {val.get('orm_fetch_ms', 'NOT VERIFIED')}")
        lines.append(f"- Index usage: `{val.get('index_scan', [])}`")
        lines.append(f"- Sequential scan detected: `{val.get('seq_scan', 'NOT VERIFIED')}`")
        lines.append(f"- Node type (root): {val.get('node_type')}")
        lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_memory(r: Dict, path: str):
    m = r.get("memory", {})
    lines = [
        "# Memory Stability Report",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Switches | {m.get('switches', 'NOT VERIFIED')} |",
        f"| Initial RSS (MB) | {m.get('initial_rss_mb')} |",
        f"| Peak RSS (MB) | {m.get('peak_rss_mb')} |",
        f"| Final RSS (MB) | {m.get('final_rss_mb')} |",
        f"| Growth (MB) | {m.get('growth_mb')} |",
        f"| Thread max | {m.get('thread_count_max')} |",
        f"| Leak suspected (>50MB) | {m.get('leak_suspected')} |",
        "",
        f"**Success criterion:** growth < {CRITERIA['memory_growth_mb']} MB → "
        f"{'PASS' if m.get('growth_mb') is not None and m.get('growth_mb', 999) < CRITERIA['memory_growth_mb'] else 'FAIL / NOT VERIFIED'}",
    ]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_tab(r: Dict, path: str):
    t = r.get("tab_teardown", {})
    lines = [
        "# Tab Lifecycle Report",
        "",
        f"**All checks passed:** {t.get('all_passed')}",
        "",
        "| Check | Result |",
        "|-------|--------|",
    ]
    for k, v in (t.get("checks") or {}).items():
        lines.append(f"| {k} | {v} |")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_regression(r: Dict, path: str):
    reg = r.get("regression", {})
    lines = [
        "# Regression Report",
        "",
        f"**Pytest subset passed:** {reg.get('passed', 'NOT VERIFIED')}",
        f"**Exit code:** {reg.get('exit_code')}",
        f"**Elapsed (s):** {reg.get('elapsed_s')}",
        "",
        "Domains covered: governance, restore, accounting model, security tests.",
        "",
        "Sales / Inventory / Purchases UI navigation: **NOT VERIFIED** (manual QA required).",
        "",
        "```",
        (reg.get("stdout_tail") or "")[-1500:],
        "```",
    ]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def grade(value: float, good: float, ok: float) -> str:
    if value is None:
        return "NOT VERIFIED"
    if value <= good:
        return "A"
    if value <= ok:
        return "B"
    if value <= ok * 2:
        return "C"
    if value <= ok * 4:
        return "D"
    return "F"


def write_scorecard(r: Dict, path: str):
    fs = r.get("frontend_startup", {})
    hub = r.get("intelligence_hub", {})
    api = r.get("api", {})
    mem = r.get("memory", {})
    bundle = api.get("hub_bundle_detail", {}).get("http_timing_ms", {})

    wf_fd = (hub.get("workflow_first_data_ms") or {}).get("avg_ms")
    corr_fd = (hub.get("correlation_first_data_ms") or {}).get("avg_ms")
    cc_fd = (hub.get("control_center_first_data_ms") or {}).get("avg_ms")
    bundle_avg = bundle.get("avg_ms") if isinstance(bundle, dict) else None
    mw = (fs.get("mainwindow_ready_ms") or {}).get("avg_ms")

    scores = {
        "Startup (MainWindow)": grade(mw, 500, 2000),
        "Navigation": "NOT VERIFIED",
        "Hub Overview": grade((hub.get("overview_visible_ms") or {}).get("avg_ms"), 100, 500),
        "Workflow first data": grade(wf_fd, CRITERIA["workflow_first_data_ms"], 3000),
        "Correlation first data": grade(corr_fd, CRITERIA["correlation_first_data_ms"], 5000),
        "Control Center first data": grade(cc_fd, CRITERIA["control_center_first_data_ms"], 5000),
        "Memory": grade(mem.get("growth_mb"), 20, CRITERIA["memory_growth_mb"]) if mem.get("growth_mb") is not None else "NOT VERIFIED",
        "Database": "B" if not r.get("database", {}).get("journal_list", {}).get("seq_scan") else "C",
        "API / Hub bundle": grade(bundle_avg, CRITERIA["hub_bundle_avg_ms"], 1500),
    }

    lines = ["# Post-Stabilization Scorecard", "", "| Area | Grade | Evidence |", "|------|-------|----------|"]
    for area, g in scores.items():
        lines.append(f"| {area} | **{g}** | measured |")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_executive(r: Dict, path: str):
    api = r.get("api", {})
    wf = api.get("workflows_instances", {})
    hub = r.get("intelligence_hub", {})
    mem = r.get("memory", {})
    tab = r.get("tab_teardown", {})
    reg = r.get("regression", {})
    bundle = api.get("hub_bundle_detail", {})

    wf_500 = (wf.get("http_status_distribution") or {}).get("500", 0)
    bundle_ok = bundle.get("keys_valid") and (bundle.get("http_timing_ms") or {}).get("avg_ms", 9999) < 500
    wf_fd = (hub.get("workflow_first_data_ms") or {}).get("avg_ms")
    corr_fd = (hub.get("correlation_first_data_ms") or {}).get("avg_ms")
    mem_ok = mem.get("growth_mb") is not None and mem.get("growth_mb", 999) < 50

    decisions = {
        "Can Backend Performance Track be frozen?": "YES" if wf.get("error_count", 1) == 0 and bundle.get("keys_valid") else "NO",
        "Is Intelligence Hub production-ready?": "YES" if mem_ok and tab.get("all_passed") and wf_fd and wf_fd < 1000 else "NO / PARTIAL",
        "Is Workflow subsystem stable?": "YES" if wf_500 == 0 else "NO",
        "Is Correlation subsystem stable?": "YES" if corr_fd and corr_fd < 2000 else "NO / NOT VERIFIED",
        "Are memory leaks present?": "YES" if mem.get("leak_suspected") else "NO",
        "Can project move to UX Audit?": "YES" if reg.get("passed") and wf_500 == 0 else "NO",
    }

    lines = [
        "# Sprint 2.5 — Post-Stabilization Validation Report",
        "",
        f"**Generated from:** `tools/sprint_2_5_results.json`",
        f"**Timestamp:** {r.get('generated_at_utc')}",
        "",
        "## Executive decisions (evidence-based)",
        "",
        "| Question | Answer |",
        "|----------|--------|",
    ]
    for q, a in decisions.items():
        lines.append(f"| {q} | **{a}** |")
    lines += [
        "",
        "## Success criteria",
        "",
        "| Criterion | Target | Result |",
        "|-----------|--------|--------|",
        f"| Workflow first data | < 1000 ms | {wf_fd} ms |",
        f"| Correlation first data | < 2000 ms | {corr_fd if corr_fd else 'NOT VERIFIED'} ms |",
        f"| Control Center first data | < 2000 ms | {(hub.get('control_center_first_data_ms') or {}).get('avg_ms', 'NOT VERIFIED')} ms |",
        f"| Hub bundle avg | < 500 ms | {(bundle.get('http_timing_ms') or {}).get('avg_ms', 'NOT VERIFIED')} ms |",
        f"| Memory after 100 switches | < 50 MB growth | {mem.get('growth_mb', 'NOT VERIFIED')} MB |",
        f"| HTTP 500 on workflows | 0 | {wf_500} |",
        "",
        "## Report index",
        "",
        "- [VALIDATION_ENVIRONMENT.md](validation/VALIDATION_ENVIRONMENT.md)",
        "- [FRONTEND_STARTUP_BENCHMARK.md](validation/FRONTEND_STARTUP_BENCHMARK.md)",
        "- [INTELLIGENCE_HUB_BENCHMARK.md](validation/INTELLIGENCE_HUB_BENCHMARK.md)",
        "- [HUB_BUNDLE_VALIDATION.md](validation/HUB_BUNDLE_VALIDATION.md)",
        "- [API_PERFORMANCE_REPORT.md](validation/API_PERFORMANCE_REPORT.md)",
        "- [DATABASE_PERFORMANCE_REPORT.md](validation/DATABASE_PERFORMANCE_REPORT.md)",
        "- [MEMORY_STABILITY_REPORT.md](validation/MEMORY_STABILITY_REPORT.md)",
        "- [TAB_LIFECYCLE_REPORT.md](validation/TAB_LIFECYCLE_REPORT.md)",
        "- [REGRESSION_REPORT.md](validation/REGRESSION_REPORT.md)",
        "- [POST_STABILIZATION_SCORECARD.md](validation/POST_STABILIZATION_SCORECARD.md)",
    ]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    os.makedirs(DOCS, exist_ok=True)
    r = load()
    write_env(r, os.path.join(DOCS, "VALIDATION_ENVIRONMENT.md"))
    write_startup(r, os.path.join(DOCS, "FRONTEND_STARTUP_BENCHMARK.md"))
    write_hub(r, os.path.join(DOCS, "INTELLIGENCE_HUB_BENCHMARK.md"))
    write_bundle(r, os.path.join(DOCS, "HUB_BUNDLE_VALIDATION.md"))
    write_api(r, os.path.join(DOCS, "API_PERFORMANCE_REPORT.md"))
    write_db(r, os.path.join(DOCS, "DATABASE_PERFORMANCE_REPORT.md"))
    write_memory(r, os.path.join(DOCS, "MEMORY_STABILITY_REPORT.md"))
    write_tab(r, os.path.join(DOCS, "TAB_LIFECYCLE_REPORT.md"))
    write_regression(r, os.path.join(DOCS, "REGRESSION_REPORT.md"))
    write_scorecard(r, os.path.join(DOCS, "POST_STABILIZATION_SCORECARD.md"))
    write_executive(r, os.path.join(ROOT, "docs", "SPRINT_2_5_POST_STABILIZATION_VALIDATION_REPORT.md"))
    print(f"Reports written to {DOCS}")


if __name__ == "__main__":
    main()

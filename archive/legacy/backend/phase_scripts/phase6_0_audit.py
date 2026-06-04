"""
Phase 6.0 - Enterprise Maintainability Refactoring Program
Master Audit Script - READ-ONLY - No Code Modifications

Produces raw data for 8 workstreams:
  WS-A: Large File Audit
  WS-B: Large Class Audit
  WS-C: Large Method Audit
  WS-D: Duplication Audit
  WS-E: Safe Extraction Map
  WS-F: Refactor Regression Matrix
  WS-G: Performance Preservation Plan
  WS-H: Refactor Priority Board
"""
import os
import re
import ast
import json
import hashlib
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

ROOT = Path(r"E:\all downloads\Pharmacy_ERP")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
OUT = ROOT / "docs" / "PHASE6_0" / "evidence"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Phase 6.0 Audit Globals
# ----------------------------------------------------------------------------
AUDIT_ID = "PHASE6_0_" + datetime.now().strftime("%Y%m%d_%H%M%S")
START_TS = datetime.now().isoformat()

# File exclusion rules (test, migration, generated, venv, archive)
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".github", "venv", ".venv", "env",
    "node_modules", "htmlcov", "migrations", "archive",
    "data", "static", "staticfiles", "logs", "coverage_governance",
    ".pytest_cache", "dist", "build", "scripts",
    "phase5_8_evidence", "phase5_9_evidence",
    "tests",  # exclude test directory from main audit (kept separate)
    ".tox", "site-packages", "media",
}

EXCLUDE_FILE_SUFFIXES = {".pyc", ".pyo", ".so", ".dll", ".exe", ".log", ".sqlite3", ".bak", ".dump", ".sql"}
EXCLUDE_FILE_NAMES = {
    "manage.py", "setup.py", "conftest.py", "wsgi.py", "asgi.py",
    "phase5_7_full.py", "phase5_7_check.py", "phase5_8_full.py", "phase5_9_full.py",
    "genesis_init.py", "audit_typo.py", "check_tb.py", "trace_startup.py",
    "debug_financial.py",
}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def count_loc(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def is_excluded_dir(p: Path) -> bool:
    parts = set(p.parts)
    return bool(parts & EXCLUDE_DIRS)

def iter_python_files(base: Path):
    for p in base.rglob("*.py"):
        if is_excluded_dir(p):
            continue
        if p.name in EXCLUDE_FILE_NAMES:
            continue
        if p.suffix in EXCLUDE_FILE_SUFFIXES:
            continue
        yield p

# ----------------------------------------------------------------------------
# WS-A: LARGE FILE AUDIT
# ----------------------------------------------------------------------------
def audit_large_files():
    results = []
    for p in iter_python_files(BACKEND):
        loc = count_loc(p)
        results.append({
            "file": str(p.relative_to(ROOT)),
            "loc": loc,
            "tier": (
                "T4_OVER_2000" if loc > 2000 else
                "T3_OVER_1500" if loc > 1500 else
                "T2_OVER_1000" if loc > 1000 else
                "T1_OVER_500" if loc > 500 else
                "OK"
            ),
        })
    for p in iter_python_files(FRONTEND):
        loc = count_loc(p)
        results.append({
            "file": str(p.relative_to(ROOT)),
            "loc": loc,
            "tier": (
                "T4_OVER_2000" if loc > 2000 else
                "T3_OVER_1500" if loc > 1500 else
                "T2_OVER_1000" if loc > 1000 else
                "T1_OVER_500" if loc > 500 else
                "OK"
            ),
        })
    results.sort(key=lambda x: -x["loc"])
    return results

# ----------------------------------------------------------------------------
# WS-B & WS-C: CLASS & METHOD AUDIT (using AST)
# ----------------------------------------------------------------------------
KEYWORDS_DECISION = {
    ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler,
    ast.With, ast.Assert, ast.BoolOp, ast.IfExp, ast.Match,
}

def cyclomatic_complexity(node: ast.AST) -> int:
    """Cyclomatic complexity (McCabe): 1 + number of decision points."""
    cc = 1
    for n in ast.walk(node):
        if isinstance(n, ast.If):
            cc += 1
        elif isinstance(n, ast.For):
            cc += 1
        elif isinstance(n, ast.While):
            cc += 1
        elif isinstance(n, ast.ExceptHandler):
            cc += 1
        elif isinstance(n, ast.With):
            cc += 1
        elif isinstance(n, ast.BoolOp):
            # and/or with k values adds k-1
            cc += max(0, len(n.values) - 1)
        elif isinstance(n, ast.IfExp):
            cc += 1
        elif isinstance(n, ast.Match):
            cc += len(n.cases)
    return cc

def max_nesting_depth(node: ast.AST) -> int:
    """Maximum nesting depth in the AST subtree."""
    def _depth(n, d):
        max_d = d
        for child in ast.iter_child_nodes(n):
            new_d = _depth(child, d + 1 if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else d)
            if new_d > max_d:
                max_d = new_d
        return max_d
    return _depth(node, 0)

def count_params(node) -> int:
    p = node.args
    n = len(p.args) + len(p.kwonlyargs) + (1 if p.vararg else 0) + (1 if p.kwarg else 0)
    return n

def collect_imports(node: ast.AST) -> set:
    imports = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for a in n.names:
                imports.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            for a in n.names:
                imports.add(f"{mod}.{a.name}" if mod else a.name)
    return imports

def count_signals(node: ast.ClassDef) -> int:
    """Count signal assignments (rough heuristic: attr access on QtCore.Signal or self.SIGNAL)."""
    count = 0
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and "signal" in t.id.lower():
                    count += 1
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Attribute) and n.func.attr.lower() in {"connect", "disconnect"}:
                count += 1
    return count

def audit_classes_and_methods():
    classes = []
    methods = []
    file_responsibilities = defaultdict(set)
    file_imports = defaultdict(set)

    for p in list(iter_python_files(BACKEND)) + list(iter_python_files(FRONTEND)):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src, filename=str(p))
        except Exception:
            continue

        file_imports[str(p.relative_to(ROOT))] = collect_imports(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count LOC of class (start_line..end_line)
                cls_loc = (node.end_lineno or 0) - (node.lineno or 0) + 1
                methods_in_cls = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                bases = [ast.unparse(b) if hasattr(ast, "unparse") else "" for b in node.bases]
                deps = collect_imports(node)
                signals = count_signals(node)
                state_vars = 0
                # Count __init__ assignments
                for m in methods_in_cls:
                    if m.name == "__init__":
                        for sub in ast.walk(m):
                            if isinstance(sub, ast.Assign):
                                for t in sub.targets:
                                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                                        state_vars += 1
                        break

                responsibilities = set()
                for m in methods_in_cls:
                    if m.name.startswith("__") and m.name not in ("__init__", "__post_init__"):
                        continue
                    responsibilities.add(m.name)

                # Module responsibility
                mod_name = p.stem
                file_responsibilities[str(p.relative_to(ROOT))].add(p.parent.name + "/" + mod_name)

                classes.append({
                    "file": str(p.relative_to(ROOT)),
                    "class": node.name,
                    "lineno": node.lineno,
                    "loc": cls_loc,
                    "method_count": len(methods_in_cls),
                    "responsibility_count": len(responsibilities),
                    "dependency_count": len(deps),
                    "signal_count": signals,
                    "state_vars": state_vars,
                    "bases": bases,
                    "tier": (
                        "T3_OVER_800" if cls_loc > 800 else
                        "T2_OVER_500" if cls_loc > 500 else
                        "T1_OVER_300" if cls_loc > 300 else
                        "OK"
                    ),
                })

                # Methods
                for m in methods_in_cls:
                    m_loc = (m.end_lineno or 0) - (m.lineno or 0) + 1
                    cc = cyclomatic_complexity(m)
                    nd = max_nesting_depth(m)
                    np_ = count_params(m)
                    deps_m = collect_imports(m)
                    methods.append({
                        "file": str(p.relative_to(ROOT)),
                        "class": node.name,
                        "method": m.name,
                        "lineno": m.lineno,
                        "loc": m_loc,
                        "cyclomatic": cc,
                        "nesting_depth": nd,
                        "params": np_,
                        "deps": len(deps_m),
                        "tier": (
                            "T3_OVER_200" if m_loc > 200 else
                            "T2_OVER_100" if m_loc > 100 else
                            "T1_OVER_50" if m_loc > 50 else
                            "OK"
                        ),
                    })
    return classes, methods, file_responsibilities, file_imports

# ----------------------------------------------------------------------------
# WS-D: DUPLICATION AUDIT
# ----------------------------------------------------------------------------
def normalize_code_block(src: str) -> str:
    """Normalize whitespace for fingerprinting."""
    s = re.sub(r"\s+", " ", src)
    s = re.sub(r"#[^\n]*", "", s)
    return s.strip()

def function_signature(node: ast.FunctionDef) -> str:
    name = node.name
    args = []
    for a in node.args.args:
        args.append(a.arg)
    return f"{name}({','.join(args)})"

def audit_duplication(classes, methods):
    """Find duplicate-ish code blocks and helper definitions."""
    func_counter = Counter()
    func_examples = defaultdict(list)
    block_fingerprints = Counter()
    block_examples = defaultdict(list)
    helper_candidates = []
    class_method_clusters = defaultdict(list)

    for p in list(iter_python_files(BACKEND)) + list(iter_python_files(FRONTEND)):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src, filename=str(p))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sig = function_signature(node)
                func_counter[sig] += 1
                func_examples[sig].append(str(p.relative_to(ROOT)))
                # short helper candidates (private, < 30 lines)
                if node.name.startswith("_") and node.end_lineno is not None and (node.end_lineno - node.lineno) < 30:
                    helper_candidates.append({
                        "file": str(p.relative_to(ROOT)),
                        "name": node.name,
                        "lineno": node.lineno,
                    })
            # Class methods grouped
            if isinstance(node, ast.ClassDef):
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        class_method_clusters[node.name].append(m.name)

    # Find duplicate method names across multiple classes (heuristic)
    method_to_classes = defaultdict(list)
    for cls_name, methods in class_method_clusters.items():
        for m in methods:
            method_to_classes[m].append(cls_name)

    # Function-body duplication: only check first 50 lines of normalized text per function
    func_body_hashes = Counter()
    func_body_examples = defaultdict(list)
    for p in list(iter_python_files(BACKEND)) + list(iter_python_files(FRONTEND)):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                src_chunk = ast.unparse(node) if hasattr(ast, "unparse") else ""
                norm = normalize_code_block(src_chunk)
                if len(norm) < 80:
                    continue
                h = hashlib.md5(norm.encode("utf-8")).hexdigest()[:10]
                func_body_hashes[h] += 1
                func_body_examples[h].append(f"{p.relative_to(ROOT)}::{node.name}")

    dup_funcs = [(sig, c, func_examples[sig][:5]) for sig, c in func_counter.most_common() if c >= 3][:50]
    dup_bodies = [(h, c, func_body_examples[h][:3]) for h, c in func_body_hashes.most_common() if c >= 2][:50]

    return {
        "duplicate_signatures": dup_funcs,
        "duplicate_bodies": dup_bodies,
        "helpers": helper_candidates,
        "method_fanout": [(m, cls) for m, cls in method_to_classes.items() if len(set(cls)) >= 3][:50],
    }

# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    print(f"=== Phase 6.0 Master Audit - {AUDIT_ID} ===", flush=True)
    print(f"Started: {START_TS}", flush=True)
    print(f"Backend root: {BACKEND}", flush=True)
    print(f"Frontend root: {FRONTEND}", flush=True)

    # WS-A
    print("\n[1/4] WS-A: Large File Audit...", flush=True)
    files = audit_large_files()
    with open(OUT / "ws_a_large_files.json", "w", encoding="utf-8") as f:
        json.dump({"audit_id": AUDIT_ID, "ts": START_TS, "files": files}, f, indent=2)
    flagged = [x for x in files if x["tier"] != "OK"]
    print(f"  Files scanned: {len(files)}, flagged: {len(flagged)}", flush=True)

    # WS-B + WS-C
    print("\n[2/4] WS-B & WS-C: Class & Method Audit...", flush=True)
    classes, methods, _file_resp, _file_imp = audit_classes_and_methods()
    with open(OUT / "ws_b_large_classes.json", "w", encoding="utf-8") as f:
        json.dump({"audit_id": AUDIT_ID, "ts": START_TS, "classes": classes}, f, indent=2)
    with open(OUT / "ws_c_large_methods.json", "w", encoding="utf-8") as f:
        json.dump({"audit_id": AUDIT_ID, "ts": START_TS, "methods": methods}, f, indent=2)
    flagged_cls = [x for x in classes if x["tier"] != "OK"]
    flagged_mth = [x for x in methods if x["tier"] != "OK"]
    print(f"  Classes: {len(classes)}, flagged: {len(flagged_cls)}", flush=True)
    print(f"  Methods: {len(methods)}, flagged: {len(flagged_mth)}", flush=True)

    # WS-D
    print("\n[3/4] WS-D: Duplication Audit...", flush=True)
    dup = audit_duplication(classes, methods)
    with open(OUT / "ws_d_duplication.json", "w", encoding="utf-8") as f:
        json.dump({"audit_id": AUDIT_ID, "ts": START_TS, **dup}, f, indent=2)
    print(f"  Duplicate signatures: {len(dup['duplicate_signatures'])}", flush=True)
    print(f"  Duplicate bodies: {len(dup['duplicate_bodies'])}", flush=True)
    print(f"  Method fan-out: {len(dup['method_fanout'])}", flush=True)

    # Summary
    print("\n[4/4] Summary...", flush=True)
    summary = {
        "audit_id": AUDIT_ID,
        "ts": START_TS,
        "total_files": len(files),
        "flagged_files": len(flagged),
        "file_tiers": {
            "T1_OVER_500": sum(1 for x in flagged if x["tier"] == "T1_OVER_500"),
            "T2_OVER_1000": sum(1 for x in flagged if x["tier"] == "T2_OVER_1000"),
            "T3_OVER_1500": sum(1 for x in flagged if x["tier"] == "T3_OVER_1500"),
            "T4_OVER_2000": sum(1 for x in flagged if x["tier"] == "T4_OVER_2000"),
        },
        "total_classes": len(classes),
        "flagged_classes": len(flagged_cls),
        "class_tiers": {
            "T1_OVER_300": sum(1 for x in flagged_cls if x["tier"] == "T1_OVER_300"),
            "T2_OVER_500": sum(1 for x in flagged_cls if x["tier"] == "T2_OVER_500"),
            "T3_OVER_800": sum(1 for x in flagged_cls if x["tier"] == "T3_OVER_800"),
        },
        "total_methods": len(methods),
        "flagged_methods": len(flagged_mth),
        "method_tiers": {
            "T1_OVER_50": sum(1 for x in flagged_mth if x["tier"] == "T1_OVER_50"),
            "T2_OVER_100": sum(1 for x in flagged_mth if x["tier"] == "T2_OVER_100"),
            "T3_OVER_200": sum(1 for x in flagged_mth if x["tier"] == "T3_OVER_200"),
        },
        "duplicate_signatures": len(dup["duplicate_signatures"]),
        "duplicate_bodies": len(dup["duplicate_bodies"]),
        "method_fanout": len(dup["method_fanout"]),
    }
    with open(OUT / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary: {summary}", flush=True)
    print(f"\nAll evidence written to: {OUT}", flush=True)

if __name__ == "__main__":
    main()

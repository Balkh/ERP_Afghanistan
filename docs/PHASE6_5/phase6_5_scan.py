"""
Phase 6.5 — Master Audit Scanner
Read-only. Scans entire repository, collects file/class/method/import metrics.
Writes JSON output to docs/PHASE6_5/raw/ for downstream analysis.
"""
import os
import sys
import ast
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("E:/all downloads/Pharmacy_ERP").resolve()
OUT = ROOT / "docs" / "PHASE6_5" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

EXCLUDE_DIRS = {
    "venv", ".venv", "env", ".env",
    "__pycache__", ".git", ".idea", ".vscode",
    "node_modules", "dist", "build", ".pytest_cache",
    "config/logs", "config\\logs",
    "migrations",  # Django auto-generated
    "raw",
}
EXCLUDE_TESTS = False  # Include test files for coupling analysis


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    for ex in EXCLUDE_DIRS:
        if ex in parts:
            return True
    if "migrations" in path.parts and path.suffix == ".py":
        # Django migrations are auto-generated, skip from metric counting
        # (but still count files for distribution)
        return False  # Count them but they won't be in "code" metrics
    return False


def sha256_of(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def loc_of(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def analyze_file(path: Path) -> dict:
    """AST analysis: classes, methods, imports."""
    rel = str(path.relative_to(ROOT))
    file_loc = loc_of(path)
    file_sha = sha256_of(path)
    rec = {
        "path": rel,
        "loc": file_loc,
        "sha256": file_sha,
        "is_migration": "migrations" in path.parts and path.suffix == ".py",
        "is_test": ("test_" in path.stem or "_test" in path.stem or "tests" in path.parts),
        "classes": [],
        "methods": [],  # All top-level + nested functions
        "imports": [],  # All import statements (local + stdlib + 3rd party)
        "from_imports": [],  # All "from X import Y" targets
    }
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src, filename=rel)
    except (SyntaxError, ValueError):
        return rec

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_methods.append({
                        "name": child.name,
                        "loc": (child.end_lineno or 0) - (child.lineno or 0) + 1,
                        "lineno": child.lineno,
                    })
            rec["classes"].append({
                "name": node.name,
                "lineno": node.lineno,
                "loc": (node.end_lineno or 0) - (node.lineno or 0) + 1,
                "methods": class_methods,
                "method_count": len(class_methods),
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Top-level functions only (not methods, which are inside classes)
            parent_is_class = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef) and node in ast.walk(parent):
                    if node.lineno > parent.lineno:
                        parent_is_class = True
                        break
            if not parent_is_class:
                rec["methods"].append({
                    "name": node.name,
                    "loc": (node.end_lineno or 0) - (node.lineno or 0) + 1,
                    "lineno": node.lineno,
                    "is_method": False,
                })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                rec["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                rec["from_imports"].append({
                    "module": node.module,
                    "names": [a.name for a in node.names],
                    "level": node.level,  # 0 = absolute, >0 = relative
                })
    return rec


def main():
    print("=" * 70)
    print("PHASE 6.5 — MASTER AUDIT SCANNER")
    print("=" * 70)
    print()

    py_files = []
    for p in ROOT.rglob("*.py"):
        if should_skip(p):
            continue
        py_files.append(p)
    py_files.sort()

    print(f"Found {len(py_files)} .py files")
    print()

    file_records = []
    total_loc = 0
    total_classes = 0
    total_methods = 0

    for i, path in enumerate(py_files):
        rec = analyze_file(path)
        if rec["is_migration"]:
            rec["loc"] = 0  # Exclude from LOC stats
        else:
            total_loc += rec["loc"]
        total_classes += len(rec["classes"])
        total_methods += len(rec["methods"])
        for cls in rec["classes"]:
            total_methods += cls["method_count"]
        file_records.append(rec)
        if (i + 1) % 200 == 0:
            print(f"  Scanned {i+1}/{len(py_files)}...")

    print(f"  Scanned {len(py_files)}/{len(py_files)}")
    print()
    print(f"Total .py files:        {len(py_files)}")
    print(f"Total LOC (non-mig):    {total_loc}")
    print(f"Total classes:          {total_classes}")
    print(f"Total methods/functions: {total_methods}")

    # Write raw output
    out_file = OUT / "raw_file_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "root": str(ROOT),
            "total_files": len(py_files),
            "total_loc": total_loc,
            "total_classes": total_classes,
            "total_methods": total_methods,
            "files": file_records,
        }, f, indent=2)
    print(f"Wrote {out_file}")
    print()

    # Quick distribution
    by_loc = sorted(file_records, key=lambda r: r["loc"], reverse=True)
    print("TOP 20 FILES BY LOC:")
    for r in by_loc[:20]:
        if r["loc"] > 0:
            print(f"  {r['loc']:5d}  {r['path']}")
    print()

    # All methods sorted by size
    all_methods = []
    for r in file_records:
        for m in r["methods"]:
            all_methods.append({
                "file": r["path"],
                "name": m["name"],
                "loc": m["loc"],
                "lineno": m["lineno"],
                "class": None,
            })
        for cls in r["classes"]:
            for m in cls["methods"]:
                all_methods.append({
                    "file": r["path"],
                    "name": f"{cls['name']}.{m['name']}",
                    "loc": m["loc"],
                    "lineno": m["lineno"],
                    "class": cls["name"],
                })
    all_methods.sort(key=lambda m: m["loc"], reverse=True)
    print("TOP 30 METHODS BY LOC:")
    for m in all_methods[:30]:
        if m["loc"] > 0:
            print(f"  {m['loc']:5d}  {m['file']}:{m['lineno']}  {m['name']}")
    print()

    # All classes sorted by size
    all_classes = []
    for r in file_records:
        for cls in r["classes"]:
            all_classes.append({
                "file": r["path"],
                "name": cls["name"],
                "loc": cls["loc"],
                "method_count": cls["method_count"],
                "lineno": cls["lineno"],
            })
    all_classes.sort(key=lambda c: c["loc"], reverse=True)
    print("TOP 20 CLASSES BY LOC:")
    for c in all_classes[:20]:
        if c["loc"] > 0:
            print(f"  {c['loc']:5d}  {c['file']}:{c['lineno']}  class {c['name']} ({c['method_count']} methods)")

    # Save methods + classes sorted
    with open(OUT / "raw_methods_sorted.json", "w", encoding="utf-8") as f:
        json.dump(all_methods, f, indent=2)
    with open(OUT / "raw_classes_sorted.json", "w", encoding="utf-8") as f:
        json.dump(all_classes, f, indent=2)
    print(f"\nWrote {OUT / 'raw_methods_sorted.json'}")
    print(f"Wrote {OUT / 'raw_classes_sorted.json'}")


if __name__ == "__main__":
    main()

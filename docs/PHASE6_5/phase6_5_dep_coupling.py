"""
Phase 6.5 — Dependency + Coupling + Circular Import Analyzer
Reads raw_file_metrics.json, builds:
  - module-level dependency graph
  - circular import detection
  - inbound/outbound coupling per module
  - orphan extraction modules
"""
import os
import sys
import ast
import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("E:/all downloads/Pharmacy_ERP").resolve()
OUT = ROOT / "docs" / "PHASE6_5" / "raw"

raw = json.loads((OUT / "raw_file_metrics.json").read_text(encoding="utf-8"))

# Index files by their dotted module name (best-effort)
def to_module_name(rel: str) -> str:
    """Convert relative path to dotted module name.
    'backend/sales/views.py' -> 'sales.views' (drop the 'backend' top dir)
    'frontend/ui/sales/x.py' -> 'frontend.ui.sales.x' (keep frontend)
    """
    parts = Path(rel).with_suffix("").parts
    if not parts:
        return ""
    # Normalize
    return ".".join(parts)


# Build local module index (set of dotted names that exist as files)
all_modules = set()
for f in raw["files"]:
    rel = f["path"]
    if rel.endswith("__init__.py"):
        # Package: "backend/sales/__init__.py" -> "sales"
        parts = Path(rel).parent.parts
    else:
        parts = Path(rel).with_suffix("").parts
    if parts:
        all_modules.add(".".join(parts))

# Reduce to backend.* and frontend.* — drop the top-level prefix
backend_modules = set()
frontend_modules = set()
for m in all_modules:
    if m.startswith("backend."):
        backend_modules.add(m[len("backend."):])
    elif m.startswith("frontend."):
        frontend_modules.add(m[len("frontend."):])

# Build dep graph: for each file, what local modules does it import?
dep_edges = []  # (source_module, target_module)
src_to_targets = defaultdict(set)
for f in raw["files"]:
    rel = f["path"]
    if rel.endswith("__init__.py"):
        src_module = ".".join(Path(rel).parent.parts)
    else:
        src_module = ".".join(Path(rel).with_suffix("").parts)
    # Strip backend. / frontend. prefix for matching
    if src_module.startswith("backend."):
        src_short = src_module[len("backend."):]
    elif src_module.startswith("frontend."):
        src_short = src_module[len("frontend."):]
    else:
        src_short = src_module
    for imp in f["from_imports"]:
        mod = imp["module"]
        # Skip stdlib / 3rd party
        if not mod:
            continue
        if mod.startswith("backend.") or mod.startswith("frontend."):
            # absolute internal import
            target = mod[len("backend."):] if mod.startswith("backend.") else mod[len("frontend."):]
        elif mod in backend_modules or mod in frontend_modules:
            target = mod
        else:
            # likely stdlib / 3rd party
            continue
        # Skip self-imports
        if target == src_short:
            continue
        dep_edges.append((src_short, target))
        src_to_targets[src_short].add(target)


# Build inbound index
target_to_sources = defaultdict(set)
for src, targets in src_to_targets.items():
    for t in targets:
        target_to_sources[t].add(src)


# Save dep graph as JSON
dep_data = {
    "backend_modules": sorted(backend_modules),
    "frontend_modules": sorted(frontend_modules),
    "edges": [{"from": s, "to": t} for s, t in dep_edges],
    "outbound": {m: sorted(list(target_to_sources)) for m, targets in src_to_targets.items() for target_to_sources in [{}]},  # placeholder
}
# Fix outbound (build it cleanly)
outbound = {m: sorted(list(t)) for m, t in src_to_targets.items()}
inbound = {m: sorted(list(s)) for m, s in target_to_sources.items()}

dep_data["outbound"] = outbound
dep_data["inbound"] = inbound

with open(OUT / "raw_dependency_graph.json", "w", encoding="utf-8") as f:
    json.dump(dep_data, f, indent=2)
print(f"Wrote {OUT / 'raw_dependency_graph.json'}")


# Circular import detection (DFS)
print()
print("=" * 70)
print("CIRCULAR IMPORT DETECTION")
print("=" * 70)

def find_cycles(graph):
    """Find all simple cycles in directed graph. Returns list of cycles."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node, start):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for nxt in graph.get(node, []):
            if nxt in rec_stack:
                # Found a cycle
                cycle_start = path.index(nxt)
                cycle = path[cycle_start:] + [nxt]
                if cycle[0] == start or len(cycle) <= 8:  # limit cycle size for readability
                    cycles.append(tuple(cycle))
            elif nxt not in visited:
                dfs(nxt, start)
        path.pop()
        rec_stack.discard(node)

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node, node)
    return cycles


# Build graph as dict
graph = {m: list(t) for m, t in src_to_targets.items()}
cycles = find_cycles(graph)
# Dedup
unique_cycles = set()
for c in cycles:
    normalized = tuple(sorted(set(c)))
    unique_cycles.add(c)

print(f"Found {len(cycles)} cycle traversals, {len(unique_cycles)} unique cycle structures")
print()
if cycles:
    print("First 20 unique cycles (up to 8 nodes each):")
    seen = set()
    count = 0
    for c in cycles:
        if c in seen:
            continue
        seen.add(c)
        if len(c) <= 8:
            print(f"  {' -> '.join(c)}")
            count += 1
            if count >= 20:
                break
else:
    print("  No circular imports detected.")


# Save cycles
with open(OUT / "raw_circular_imports.json", "w", encoding="utf-8") as f:
    json.dump({
        "cycle_count": len(cycles),
        "unique_structures": len(unique_cycles),
        "cycles": [list(c) for c in cycles[:200]],  # cap output
    }, f, indent=2)
print(f"Wrote {OUT / 'raw_circular_imports.json'}")


# Coupling: top modules by inbound
print()
print("=" * 70)
print("COUPLING ANALYSIS")
print("=" * 70)

# Inbound: who's importing me (afferent coupling)
inbound_count = {m: len(s) for m, s in target_to_sources.items()}
inbound_sorted = sorted(inbound_count.items(), key=lambda x: -x[1])

# Outbound: what I'm importing (efferent coupling)
outbound_count = {m: len(t) for m, t in src_to_targets.items()}
outbound_sorted = sorted(outbound_count.items(), key=lambda x: -x[1])

# Instability = efferent / (efferent + afferent) [0=stable, 1=unstable]
instability = {}
for m in set(list(inbound_count.keys()) + list(outbound_count.keys())):
    e = outbound_count.get(m, 0)
    a = inbound_count.get(m, 0)
    if e + a == 0:
        instability[m] = 0.0
    else:
        instability[m] = e / (e + a)

print("\nTOP 20 BY INBOUND COUPLING (most-imported modules):")
for m, n in inbound_sorted[:20]:
    print(f"  {n:4d}  {m}")

print("\nTOP 20 BY OUTBOUND COUPLING (most-importing modules):")
for m, n in outbound_sorted[:20]:
    print(f"  {n:4d}  {m}")

print("\nTOP 15 MOST UNSTABLE (high efferent / low afferent):")
unstable_sorted = sorted(instability.items(), key=lambda x: -x[1])
for m, score in unstable_sorted[:15]:
    if score > 0:
        e = outbound_count.get(m, 0)
        a = inbound_count.get(m, 0)
        print(f"  {score:.2f}  (e={e}, a={a})  {m}")

# Save
with open(OUT / "raw_coupling.json", "w", encoding="utf-8") as f:
    json.dump({
        "inbound_sorted": [{"module": m, "count": n} for m, n in inbound_sorted],
        "outbound_sorted": [{"module": m, "count": n} for m, n in outbound_sorted],
        "instability_sorted": [{"module": m, "instability": s} for m, s in unstable_sorted],
    }, f, indent=2)
print(f"\nWrote {OUT / 'raw_coupling.json'}")


# Orphan extraction module detection
print()
print("=" * 70)
print("ORPHAN EXTRACTION MODULE DETECTION")
print("=" * 70)

# An "extraction module" is a file in a backup/extracts/ subfolder or docs/PHASE6_*/evidence/
# that we want to check is still referenced correctly

# Check: are all docs/PHASE6_*/evidence/*_BEFORE.py unused by current code? (they should be — they're backups)
# Check: are all docs/PHASE6_*/scripts/ unused? (likely yes — audit scripts)
# Check: are there any extraction modules created by Phase 6.2 (backend/backup/extracts/) that are referenced?

extraction_paths = [
    "backend/backup/extracts",
    "docs/PHASE6_2/evidence",
    "docs/PHASE6_3/evidence",
    "docs/PHASE6_4/evidence",
    "docs/PHASE6_5",  # this audit's own dir
]
print()
orphan_results = {}
for ep in extraction_paths:
    ep_full = ROOT / ep
    if not ep_full.exists():
        continue
    py_files = list(ep_full.rglob("*.py"))
    if not py_files:
        continue
    print(f"\n{ep}:")
    for pf in py_files:
        rel = str(pf.relative_to(ROOT))
        # Count how many OTHER files import this one
        target_name = pf.stem  # filename without .py
        # Build a set of plausible dotted names
        dotted_candidates = set()
        parts = Path(rel).with_suffix("").parts
        if rel.endswith("__init__.py"):
            dotted_candidates.add(".".join(Path(rel).parent.parts))
        else:
            dotted_candidates.add(".".join(parts))
        # Strip backend./frontend. prefix variants
        for c in list(dotted_candidates):
            if c.startswith("backend."):
                dotted_candidates.add(c[len("backend."):])
            if c.startswith("frontend."):
                dotted_candidates.add(c[len("frontend."):])
        # Search for any import that references this
        ref_count = 0
        ref_sources = []
        for f in raw["files"]:
            if f["path"] == rel:
                continue
            for imp in f["from_imports"]:
                if imp["module"] in dotted_candidates:
                    ref_count += 1
                    ref_sources.append(f["path"])
        is_orphan = (ref_count == 0)
        marker = "[ORPHAN]" if is_orphan else f"[ref'd by {ref_count}]"
        print(f"  {marker}  {rel}")
        if ref_count > 0 and ref_count <= 5:
            for s in ref_sources:
                print(f"             <- {s}")
        orphan_results[rel] = {
            "orphan": is_orphan,
            "ref_count": ref_count,
            "ref_sources": ref_sources,
        }

with open(OUT / "raw_orphans.json", "w", encoding="utf-8") as f:
    json.dump(orphan_results, f, indent=2)
print(f"\nWrote {OUT / 'raw_orphans.json'}")

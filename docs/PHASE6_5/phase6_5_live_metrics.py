"""
Phase 6.5 — Filtered metrics: exclude docs/PHASE6_*/evidence/* and archive/
to get a "live codebase" view.
"""
import json
from pathlib import Path

ROOT = Path("E:/all downloads/Pharmacy_ERP").resolve()
OUT = ROOT / "docs" / "PHASE6_5" / "raw"

raw = json.loads((OUT / "raw_file_metrics.json").read_text(encoding="utf-8"))

EXCLUDE_PATH_PREFIXES = (
    "docs/PHASE6_2/evidence/",
    "docs/PHASE6_3/evidence/",
    "docs/PHASE6_4/evidence/",
    "docs/PHASE6_5/",
    "archive/",
)

live_files = []
for f in raw["files"]:
    rel = f["path"].replace("\\", "/")
    if any(rel.startswith(p) for p in EXCLUDE_PATH_PREFIXES):
        continue
    if f["is_migration"]:
        continue
    live_files.append(f)

live_loc = sum(f["loc"] for f in live_files)
print("=" * 70)
print("LIVE CODEBASE METRICS (excluding evidence backups + archive)")
print("=" * 70)
print(f"Live .py files: {len(live_files)} (raw: {raw['total_files']})")
print(f"Live LOC: {live_loc:,} (raw: {raw['total_loc']:,})")
print()

# Top 30 live files by LOC
live_sorted = sorted(live_files, key=lambda f: f["loc"], reverse=True)
print("TOP 30 LIVE FILES BY LOC:")
for f in live_sorted[:30]:
    if f["loc"] > 100:
        print(f"  {f['loc']:5d}  {f['path']}")
print()

# All live methods sorted by size
all_methods = []
for f in live_files:
    for m in f["methods"]:
        all_methods.append({"file": f["path"], "name": m["name"], "loc": m["loc"],
                            "lineno": m["lineno"], "class": None, "is_top_level": True})
    for cls in f["classes"]:
        for m in cls["methods"]:
            all_methods.append({"file": f["path"], "name": f"{cls['name']}.{m['name']}",
                                "loc": m["loc"], "lineno": m["lineno"],
                                "class": cls["name"], "is_top_level": False})
all_methods.sort(key=lambda m: m["loc"], reverse=True)

print("TOP 30 LIVE METHODS BY LOC:")
for m in all_methods[:30]:
    if m["loc"] > 50:
        print(f"  {m['loc']:5d}  {m['file']}:{m['lineno']}  {m['name']}")
print()

# Top 30 live classes
all_classes = []
for f in live_files:
    for cls in f["classes"]:
        all_classes.append({"file": f["path"], "name": cls["name"], "loc": cls["loc"],
                            "method_count": cls["method_count"], "lineno": cls["lineno"]})
all_classes.sort(key=lambda c: c["loc"], reverse=True)
print("TOP 20 LIVE CLASSES BY LOC:")
for c in all_classes[:20]:
    if c["loc"] > 100:
        print(f"  {c['loc']:5d}  {c['file']}:{c['lineno']}  class {c['name']} ({c['method_count']} methods)")
print()

# Distribution buckets
def bucketize(items, key, buckets):
    out = {b: 0 for b in buckets}
    for it in items:
        v = key(it)
        for b in buckets:
            if "<" in b:
                threshold = int(b.split("<")[1].rstrip(")"))
                if v < threshold:
                    out[b] += 1
                    break
            elif ">=" in b:
                threshold = int(b.split(">=")[1])
                if v >= threshold:
                    out[b] += 1
                    break
    return out

print("METHOD SIZE DISTRIBUTION (live):")
buckets = ["<25", "<50", "<100", "<200", "<300", ">=300"]
dist = bucketize(all_methods, lambda m: m["loc"], buckets)
total = sum(dist.values())
for b, n in dist.items():
    pct = (n / total * 100) if total else 0
    print(f"  {b:>6}  {n:5d}  {pct:5.1f}%")
print()

print("FILE SIZE DISTRIBUTION (live):")
buckets_f = ["<100", "<300", "<500", "<1000", "<2000", ">=2000"]
dist_f = bucketize(live_files, lambda f: f["loc"], buckets_f)
total_f = sum(dist_f.values())
for b, n in dist_f.items():
    pct = (n / total_f * 100) if total_f else 0
    print(f"  {b:>6}  {n:5d}  {pct:5.1f}%")
print()

print("CLASS SIZE DISTRIBUTION (live):")
buckets_c = ["<50", "<100", "<200", "<500", "<1000", ">=1000"]
dist_c = bucketize(all_classes, lambda c: c["loc"], buckets_c)
total_c = sum(dist_c.values())
for b, n in dist_c.items():
    pct = (n / total_c * 100) if total_c else 0
    print(f"  {b:>6}  {n:5d}  {pct:5.1f}%")

# Save filtered metrics
with open(OUT / "raw_live_metrics.json", "w", encoding="utf-8") as f:
    json.dump({
        "live_files": len(live_files),
        "live_loc": live_loc,
        "live_methods": len(all_methods),
        "live_classes": len(all_classes),
        "method_dist": dist,
        "file_dist": dist_f,
        "class_dist": dist_c,
        "top_files": [{"path": f["path"], "loc": f["loc"]} for f in live_sorted[:50] if f["loc"] > 0],
        "top_methods": [m for m in all_methods if m["loc"] > 50][:100],
        "top_classes": [c for c in all_classes if c["loc"] > 0][:50],
    }, f, indent=2)
print(f"\nWrote {OUT / 'raw_live_metrics.json'}")

#!/usr/bin/env python3
"""CLI entry point for enterprise UX certifier. Exits 0 only if PRODUCTION_READY."""
import sys, json
sys.path.insert(0, ".")
from enterprise_certification.certifier import run_certification

report = run_certification()
verdict = report.get("final_verdict", "OPERATIONALLY_UNSAFE")
avg_score = report.get("average_score", 0)
print("Final Verdict:", verdict)
print("Average Score:", avg_score)
print()
for key, status in report.items():
    if key in ("final_verdict", "average_score", "details"):
        continue
    print(f"  {key:30s} {status}")
print()
print("Score Breakdown:")
for key, details in report.get("details", {}).items():
    score = details.get("score", 0)
    print(f"  {key:30s} {score:5.1f}%")
print()
if verdict == "PRODUCTION_READY" and avg_score >= 90:
    print("[APPROVED] ENTERPRISE UX CERTIFICATION PASSED")
    sys.exit(0)
else:
    print("[BLOCKED] ENTERPRISE UX CERTIFICATION FAILED")
    if avg_score < 90:
        print(f"  - Average score {avg_score:.1f}% is below 90% threshold")
    if verdict != "PRODUCTION_READY":
        print(f"  - Verdict is '{verdict}', expected 'PRODUCTION_READY'")
    sys.exit(1)

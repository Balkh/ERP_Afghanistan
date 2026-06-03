#!/usr/bin/env python3
"""
Screen Migration Audit Tool.
Tracks which screens have been migrated to the Enterprise component architecture.

Usage:
    python scripts/screen_migration_audit.py
    python scripts/screen_migration_audit.py --detail
    python scripts/screen_migration_audit.py --json
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

FRONTEND_DIR = Path(__file__).parent.parent
UI_DIR = FRONTEND_DIR / "ui"

MIGRATION_RULES = {
    "enterprise_button": {
        "good": "EnterpriseButton",
        "bad": ["QPushButton", "ButtonRenderer"],
        "weight": 2,
    },
    "enterprise_table": {
        "good": "EnterpriseTable",
        "bad": ["QTableWidget", "TableRenderer"],
        "weight": 3,
    },
    "enterprise_form": {
        "good": "EnterpriseForm",
        "bad": ["QFormLayout", "FormField"],
        "weight": 2,
    },
    "enterprise_dialog": {
        "good": "EnterpriseDialog",
        "bad": ["QDialog", "DialogRenderer"],
        "weight": 2,
    },
    "semantic_typo": {
        "good": ["TEXT_PAGE_TITLE", "TEXT_SECTION_TITLE", "TEXT_CARD_TITLE",
                 "TEXT_BODY", "TEXT_LABEL", "TEXT_TABLE"],
        "bad": ["QFont("],
        "weight": 1,
    },
    "color_tokens": {
        "good": ["COLOR_"],
        "bad": ["#"],
        "weight": 1,
    },
    "base_screen": {
        "good": "BaseScreen",
        "bad": [],
        "weight": 1,
    },
    "spacing_tokens": {
        "good": ["SPACING_", "MARGIN_", "PADDING_"],
        "bad": [],
        "weight": 1,
    },
}


def scan_screen(filepath: Path) -> Dict:
    """Scan a single screen file for migration compliance."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {"error": "unreadable", "score": 0}

    results = {}
    total_weight = 0
    earned_weight = 0

    for rule_name, rule in MIGRATION_RULES.items():
        good_list = rule["good"] if isinstance(rule["good"], list) else [rule["good"]]
        bad_list = rule["bad"] if isinstance(rule["bad"], list) else [rule["bad"]]

        has_good = any(g in text for g in good_list)
        has_bad = any(b in text for b in bad_list)

        if has_good and not has_bad:
            results[rule_name] = "compliant"
            earned_weight += rule["weight"]
        elif has_good and has_bad:
            results[rule_name] = "partial"
            earned_weight += rule["weight"] * 0.5
        elif has_bad:
            results[rule_name] = "violation"
        else:
            results[rule_name] = "not_applicable"

        total_weight += rule["weight"]

    score = (earned_weight / total_weight * 100) if total_weight > 0 else 0
    return {"results": results, "score": round(score, 1)}


def main():
    detail = "--detail" in sys.argv
    as_json = "--json" in sys.argv

    screens = []
    for py_file in sorted(UI_DIR.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        if py_file.name in ("__init__.py", "constants.py"):
            continue
        screens.append(py_file)

    report = {}
    total_score = 0
    for f in screens:
        rel = str(f.relative_to(FRONTEND_DIR))
        result = scan_screen(f)
        report[rel] = result
        total_score += result["score"]

    avg_score = total_score / len(screens) if screens else 0

    if as_json:
        print(json.dumps({
            "total_screens": len(screens),
            "average_score": round(avg_score, 1),
            "screens": report,
        }, indent=2))
        return

    print("=" * 70)
    print("SCREEN MIGRATION AUDIT")
    print("=" * 70)
    print(f"Total screens scanned: {len(screens)}")
    print(f"Average migration score: {avg_score:.1f} / 100")
    print()
    print("Score ranges:")
    print("  80-100: Compliant (migrated)")
    print("  50-79:  In progress")
    print("  0-49:   Not migrated")
    print()

    by_level = {"compliant": 0, "in_progress": 0, "not_migrated": 0}
    for f, result in report.items():
        if result["score"] >= 80:
            level = "compliant"
        elif result["score"] >= 50:
            level = "in_progress"
        else:
            level = "not_migrated"
        by_level[level] += 1

    print(f"Compliant:    {by_level['compliant']}")
    print(f"In progress:  {by_level['in_progress']}")
    print(f"Not migrated: {by_level['not_migrated']}")
    print()

    if detail:
        print("-" * 70)
        print("DETAILED SCREEN REPORT")
        print("-" * 70)
        for f, result in sorted(report.items(), key=lambda x: x[1]["score"]):
            level = "OK" if result["score"] >= 80 else "!!" if result["score"] >= 50 else "XX"
            violations = [k for k, v in result["results"].items() if v == "violation"]
            print(f"  [{level}] {result['score']:5.1f}  {f}" + (f"  violations: {violations}" if violations else ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())

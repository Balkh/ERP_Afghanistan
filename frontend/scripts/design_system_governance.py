"""
Design System Governance Scanner.
Read-only scanner that detects raw styling values bypassing semantic tokens.

Usage:
    python scripts/design_system_governance.py
    python scripts/design_system_governance.py --strict   # includes hex check

Exit codes:
    0 = clean
    1 = violations found
"""

import re
import sys
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

EXCLUDE_FILES = {
    "printable_invoice.py",  # HTML template — uses its own CSS
    "theme_manager.py",      # Deprecated, kept for backward compat
    "constants.py",          # Token definitions — false positives
}

# Mappable values that SHOULD use tokens
PADDING_VALUES = {4: "SPACING_XS", 8: "SPACING_SM", 12: "SPACING_MD",
                  16: "SPACING_LG", 20: "SPACING_XL", 24: "SPACING_XXL", 6: "SPACING_6"}
RADIUS_VALUES = {4: "BORDER_RADIUS_SM", 6: "BORDER_RADIUS_MD", 8: "BORDER_RADIUS_LG",
                 12: "BORDER_RADIUS_XL", 2: "BORDER_RADIUS_XS"}
FONT_VALUES = {8: "FONT_SIZE_8", 9: "FONT_SIZE_XS", 10: "FONT_SIZE_SM", 11: "FONT_SIZE_MD",
               12: "FONT_SIZE_LG", 13: "FONT_SIZE_XL", 14: "FONT_SIZE_XXL", 16: "FONT_SIZE_16",
               18: "FONT_SIZE_TITLE", 20: "FONT_SIZE_HEADER", 22: "FONT_SIZE_SECTION",
               24: "FONT_SIZE_24", 28: "FONT_SIZE_28"}

ALLOWED_PATTERNS = {
    "font-size": FONT_VALUES,
    "padding": PADDING_VALUES,
    "border-radius": RADIUS_VALUES,
}


def scan_file(filepath: Path, strict: bool = False) -> list:
    violations = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations

    for i, line in enumerate(text.split("\n"), 1):
        for label, value_map in ALLOWED_PATTERNS.items():
            pattern = rf'{label}:\s*(\d+)px'
            for match in re.finditer(pattern, line):
                val = int(match.group(1))
                token = value_map.get(val)
                if token is None:
                    continue  # No token exists for this value — skip
                before = line[: match.start()]
                if "{" in before[max(0, match.start() - 3) : match.start()]:
                    continue  # Already tokenized
                violations.append((label, val, token, i, match.group(), filepath))

        if strict and not filepath.name.startswith("constants"):
            for match in re.finditer(r'#[0-9a-fA-F]{6}\b', line):
                before = line[: match.start()]
                # Skip COLOR_* definitions
                if "COLOR_" in before or "= " in before:
                    continue
                violations.append(("hex", 0, "", i, match.group(), filepath))

    return violations


def main():
    strict = "--strict" in sys.argv
    all_violations = []

    for py_file in sorted(UI_DIR.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        if py_file.name in EXCLUDE_FILES:
            continue
        all_violations.extend(scan_file(py_file, strict))

    if not all_violations:
        print("DESIGN SYSTEM GOVERNANCE: CLEAN")
        print("No tokenizable styling violations detected.")
        return 0

    print("DESIGN SYSTEM GOVERNANCE: VIOLATIONS FOUND")
    print(f"Total: {len(all_violations)} violations (use `--strict` for hex check)\n")

    by_type: dict = {}
    for label, val, token, line, match, fpath in all_violations:
        rel = fpath.relative_to(UI_DIR.parent)
        by_type.setdefault(label, []).append(f"{rel}:{line}: {match} -> {token}")

    for label in ["font-size", "padding", "border-radius", "hex"]:
        items = by_type.get(label, [])
        if items:
            plural = f" ({len(items)} occurrences)"
            print(f"[{label}]{plural}")
            for item in items[:8]:
                print(f"  {item}")
            if len(items) > 8:
                print(f"  ... and {len(items) - 8} more")
            print()

    return 1


if __name__ == "__main__":
    sys.exit(main())

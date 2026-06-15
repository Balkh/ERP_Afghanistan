"""Regression guard: every lazy screen registry target must import and expose its class."""
import importlib
import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")


def test_screen_registry_targets_importable():
    registry_path = Path(__file__).resolve().parents[2] / "ui" / "screen_registry.py"
    text = registry_path.read_text(encoding="utf-8")
    targets = re.findall(r'"(ui\.[^"]+)",\s*"([A-Za-z_][A-Za-z0-9_]*)"', text)
    assert targets, "No screen registry targets found"

    failures = []
    for module_path, class_name in targets:
        try:
            module = importlib.import_module(module_path)
            getattr(module, class_name)
        except Exception as exc:  # pragma: no cover - assertion reports details
            failures.append(f"{module_path}.{class_name}: {type(exc).__name__}: {exc}")

    assert not failures, "Unimportable screen registry targets:\n" + "\n".join(failures)

"""Reusable UI test helper shims used by tests.utils exports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest


@dataclass
class WidgetTestData:
    values: Dict[str, Any] = field(default_factory=dict)


class UITestHelpers:
    @staticmethod
    def assert_visible(widget):
        assert widget is not None
        if hasattr(widget, "isVisible"):
            assert widget.isVisible()

    @staticmethod
    def assert_text(widget, expected: str):
        assert widget is not None
        assert widget.text() == expected


class FormValidationTester:
    def __init__(self):
        self.errors: Dict[str, str] = {}

    def require(self, name: str, value: Any):
        if value in (None, ""):
            self.errors[name] = "required"
        return not self.errors


class TableTestHelper:
    @staticmethod
    def row_count(table) -> int:
        return table.rowCount() if hasattr(table, "rowCount") else 0


class NavigationTestHelper:
    def __init__(self):
        self.history: List[Any] = []

    def record(self, target):
        self.history.append(target)


class PerformanceTestHelper:
    def __init__(self):
        self.measurements: List[float] = []

    def record(self, value: float):
        self.measurements.append(value)


class KeyboardWorkflowTester:
    def __init__(self):
        self.events: List[Any] = []

    def record(self, event):
        self.events.append(event)


@pytest.fixture
def enterprise_button():
    return None


@pytest.fixture
def enterprise_table():
    return None


@pytest.fixture
def form_field():
    return None


@pytest.fixture
def notification_manager():
    return None


@pytest.fixture
def locale_manager():
    return None


@pytest.fixture
def date_formatter():
    return lambda value: str(value)


@pytest.fixture
def currency_formatter():
    return lambda value: f"{float(value):,.2f}"

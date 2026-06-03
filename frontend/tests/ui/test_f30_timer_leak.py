"""F-30 Timer Leak Remediation — verify observability dashboards
clean up their AsyncDataLoader timers on hideEvent().

Phase 5.5 finding F-30: observability/dashboards.py had 7 loader.start()
calls and 1 loader.stop() call (via the unused cleanup() method).
Phase 5.6 fix: _on_screen_hidden() calls cleanup() so each navigation
cycle stops all loaders.
"""
import os
import sys

import pytest

pytestmark = pytest.mark.qt


@pytest.fixture(scope="module")
def qapp():
    """Provide a QApplication for the test module."""
    from PySide6.QtWidgets import QApplication
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    app.processEvents()


@pytest.fixture
def api_client_mock():
    """Return a MagicMock that responds to .get() with a valid payload."""
    from unittest.mock import MagicMock
    client = MagicMock()
    client.get = MagicMock(return_value={"data": {}, "results": []})
    return client


def _make_dashboard(qapp, api_client_mock, screen_cls):
    """Helper: construct a dashboard and process pending events."""
    from PySide6.QtCore import QCoreApplication
    instance = screen_cls(api_client_mock)
    QCoreApplication.processEvents()
    return instance


def test_observability_main_screen_timers_cleared_on_hide(qapp, api_client_mock):
    """On hide, every AsyncDataLoader must be stopped."""
    from runtime import timer_registry
    from ui.observability.dashboards import ObservabilityMainScreen

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, ObservabilityMainScreen)

    screen._on_screen_hidden()
    qapp.processEvents()

    assert timer_registry.active_timer_count() <= initial, (
        f"Timer count grew from {initial} to "
        f"{timer_registry.active_timer_count()} after _on_screen_hidden(); cleanup() did not run."
    )


def test_control_center_dashboard_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import ControlCenterDashboard

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, ControlCenterDashboard)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_unified_timeline_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import UnifiedTimelineView

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, UnifiedTimelineView)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_incident_intelligence_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import IncidentIntelligenceView

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, IncidentIntelligenceView)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_predictive_drift_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import PredictiveDriftDashboard

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, PredictiveDriftDashboard)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_replay_time_travel_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import ReplayTimeTravelView

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, ReplayTimeTravelView)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_digital_twin_telemetry_timers_cleared_on_hide(qapp, api_client_mock):
    from runtime import timer_registry
    from ui.observability.dashboards import DigitalTwinTelemetryView

    timer_registry.shutdown_all_timers()
    initial = timer_registry.active_timer_count()
    screen = _make_dashboard(qapp, api_client_mock, DigitalTwinTelemetryView)
    screen._on_screen_hidden()
    qapp.processEvents()
    assert timer_registry.active_timer_count() <= initial


def test_navigation_cycle_no_orphan_timers(qapp, api_client_mock):
    """Simulate 10 open/close cycles — timer count must not grow."""
    from runtime import timer_registry
    from ui.observability.dashboards import ObservabilityMainScreen

    timer_registry.shutdown_all_timers()
    baseline = timer_registry.active_timer_count()

    for _ in range(10):
        screen = _make_dashboard(qapp, api_client_mock, ObservabilityMainScreen)
        screen._on_screen_hidden()
        qapp.processEvents()

    final = timer_registry.active_timer_count()
    assert final == baseline, (
        f"After 10 navigation cycles, timer count grew from "
        f"{baseline} to {final} (leak of {final - baseline} timers)."
    )

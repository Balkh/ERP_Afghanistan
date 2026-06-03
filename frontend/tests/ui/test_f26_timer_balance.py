"""F-26 Timer Imbalance Remediation — verify all 4 F-26 files
have balanced timer start/stop counts.

Phase 5.5 finding F-26: 5 files had 8 timer starts without matching
stops. Phase 5.6 fixes:
  - frontend/ui/main_window.py: status_timer, connection_timer
    stopped in closeEvent
  - frontend/ui/common/product_selection_dialog.py: search_timer
    stopped in done()
  - frontend/ui/system/licensing_screen.py: _timer stopped in
    _on_screen_hidden()
  - frontend/ui/accounting/report_browser.py: was a false positive
    (worker.start() is QThread.start(), not QTimer.start())

This is a static-analysis test that re-scans the files and verifies
the balance is 0.
"""
import os
import re


_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND = os.path.abspath(os.path.join(_HERE, '..', '..'))


FILES = [
    os.path.join(_FRONTEND, 'ui/main_window.py'),
    os.path.join(_FRONTEND, 'ui/accounting/report_browser.py'),
    os.path.join(_FRONTEND, 'ui/common/product_selection_dialog.py'),
    os.path.join(_FRONTEND, 'ui/system/licensing_screen.py'),
]


def _read_file(path: str) -> str:
    with open(path, 'rb') as fh:
        raw = fh.read()
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1', errors='replace')


def _count_qtimer_starts(content: str) -> int:
    """Count only QTimer.start() calls, not QThread.start().

    We require a `QTimer` token before the `.start(` call. A QThread
    reference like `self.worker.start()` is excluded.
    """
    pattern = re.compile(r'QTimer\b.*?\.start\s*\(', re.DOTALL)
    return len(pattern.findall(content))


def _count_qtimer_stops(content: str) -> int:
    """Count QTimer.stop() calls — only those preceded by a QTimer
    reference (not generic .stop() calls on QThread or other objects)."""
    pattern = re.compile(r'(?:self\.|QTimer\b).*?\.stop\s*\(', re.DOTALL)
    return len(pattern.findall(content))


def test_main_window_balance():
    content = _read_file(FILES[0])
    starts = _count_qtimer_starts(content)
    stops = _count_qtimer_stops(content)
    assert starts == 2, f"Expected 2 QTimer starts in main_window.py, got {starts}"
    assert stops == 2, f"Expected 2 QTimer stops in main_window.py, got {stops}"
    assert starts - stops == 0, (
        f"main_window.py: timer balance is {starts - stops} (must be 0)"
    )


def test_product_selection_dialog_balance():
    content = _read_file(FILES[2])
    starts = _count_qtimer_starts(content)
    stops = _count_qtimer_stops(content)
    assert starts - stops == 0, (
        f"product_selection_dialog.py: balance is {starts - stops} (must be 0)"
    )


def test_licensing_screen_balance():
    content = _read_file(FILES[3])
    starts = _count_qtimer_starts(content)
    stops = _count_qtimer_stops(content)
    assert starts - stops == 0, (
        f"licensing_screen.py: balance is {starts - stops} (must be 0)"
    )


def test_report_browser_no_qtimer_leak():
    """report_browser.py should have 0 QTimer leaks (worker is QThread)."""
    content = _read_file(FILES[1])
    starts = _count_qtimer_starts(content)
    assert starts == 0, (
        f"report_browser.py has {starts} QTimer starts "
        f"(only QThread.start() is expected — no QTimer)"
    )


def test_all_f26_files_have_zero_balance():
    """End-to-end: scan all F-26 files and verify balance == 0."""
    for f in FILES:
        content = _read_file(f)
        starts = _count_qtimer_starts(content)
        stops = _count_qtimer_stops(content)
        balance = starts - stops
        assert balance == 0, (
            f"{f}: starts={starts} stops={stops} balance={balance} (must be 0)"
        )


def test_main_window_closeEvent_stops_status_timer():
    """Regression: main_window.closeEvent must stop status_timer."""
    content = _read_file(FILES[0])
    assert 'status_timer.stop()' in content, (
        "main_window.closeEvent must call status_timer.stop()"
    )
    assert 'connection_timer.stop()' in content, (
        "main_window.closeEvent must call connection_timer.stop()"
    )


def test_product_selection_dialog_done_stops_search_timer():
    """Regression: ProductSelectionDialog.done must stop search_timer."""
    content = _read_file(FILES[2])
    assert 'search_timer.stop()' in content, (
        "ProductSelectionDialog.done() must call search_timer.stop()"
    )


def test_licensing_screen_hidden_stops_timer():
    """Regression: LicensingScreen._on_screen_hidden must stop _timer."""
    content = _read_file(FILES[3])
    assert '_timer.stop()' in content, (
        "LicensingScreen._on_screen_hidden() must call _timer.stop()"
    )

# Root Cause Analysis (synthesized from automated scan)

Summary:
- Wide class of issues stem from incomplete signal-slot bindings: 40 frontend modules show missing connect targets (see `audit_reports_auto/connect_problems_summary.md`). Many screens report missing `self.save`, `self.load_*`, or `_on_*` handlers.
- Multiple UI timers (`QTimer.timeout.connect`) exist across dashboard, main_window, integrity screens and many others — causing frequent polling and duplicate API calls which amplify backend errors under load.
- Backup and restore services (`backend/backup/*`) include many broad `except Exception as e:` handlers. These swallow errors and log tracebacks, leading to silent failures and inconsistent state during recovery operations.
- Several frontend screens manipulate tables and row counts directly (`setRowCount`, `removeRow`, `insertRow`) without deferred rendering or chunking; this can block the GUI thread on large datasets.
- Navigation mapping is intact: `frontend/ui/screen_registry.py` entries resolve to existing modules (no missing modules detected by registry parser). However, many registered screens have partial wiring (connect_status != CONNECTED).
- Backend provides ViewSets for core entities (inventory ProductViewSet, SalesInvoiceViewSet, etc.) but frontend-to-backend API usages are scattered; some frontend modules use `requests`/`api.client` lines with no uniform error handling or retry, increasing risk of unhandled failures.

Root causes (evidence-based):
1. Signal/Slot Drift after migration: refactors changed or removed handler method names without updating `.connect(...)` sites. Evidence: `connect_analysis.json` and `connect_problems_summary.md` listing missing `self.<name>` targets across ~40 files.
2. Polling/Timer Storms: Many screens use `QTimer` or `timeout.connect` for periodic refresh; no central backoff or coordination leads to overlapping requests. Evidence: `08_performance_recovery_report.md` lists timer-using files (dashboard, main_window, integrity screens, licensing, etc.).
3. Silent exception swallowing in mission-critical services: numerous `except Exception as e:` blocks in `backend/backup/*`, `backend/genesis_init.py`, and governance modules mask root exceptions and prevent recovery flows from surfacing actionable failures.
4. Non-atomic UI operations and main-thread blocking: table row mutations and heavy synchronous loads block the UI and make screens appear unresponsive. Evidence: `08_performance_recovery_report.md` shows files with table row operations and `frontend/ui/components` containing `set_data` patterns.
5. Inconsistent frontend-backend contracts around actions: workflows rely on DRF `@action` methods but frontend sometimes calls different endpoints or performs client-side workflow steps expecting synchronous immediate success. Evidence: `06_workflow_integrity_report.md` outlines available `@action` hooks; mismatch cases appear when frontend assumes a `receive`/`post` action but backend has a differently named action.
6. Partial dialog parent-refresh gaps: analysis of dialogs (see `05_dialog_integrity_report.md`) shows dialogs without explicit parent-refresh calls after accept; many dialogs rely on implicit behavior that may have changed after BaseScreen migration.

High-risk areas:
- Backup & Restore (`backend/backup/*`): broad excepts + many actions -> critical for operational recovery.
- Sales / Purchases invoice screens (`frontend/ui/sales/*`, `frontend/ui/purchases/*`): central workflows; missing handlers here block business operations.
- Main navigation event handlers in `main_window.py` and `sidebar.py`: if these miswire, users cannot reach screens reliably.

Next-evidence pointers (quick checks to confirm before fixes):
- Open `audit_reports_auto/connect_problems_summary.md` and inspect top missing targets in `frontend/ui/sales/sales_invoice_screen.py`, `frontend/ui/inventory/product_screen.py`, `frontend/ui/sales/customer_screen.py`, `frontend/ui/purchases/supplier_screen.py`.
- Review `backend/backup/views.py` and `backend/backup/services/restore_service.py` for broad except blocks that swallow exceptions; add explicit error propagation in a subsequent patch (diagnosis only now).


# Operational Recovery Plan (prioritized)

Guiding principles: do NOT refactor broadly — make minimal surgical fixes that restore operational behavior. Provide roll-forward proof-of-fix steps and verification commands.

Priority 1 — System Breaking (Fix now)
- Backup & Restore stability
  - Severity: CRITICAL
  - Business impact: System restore/backup failures block recovery and deployments
  - Effort: Medium (1-2 dev days)
  - Affected files: `backend/backup/views.py`, `backend/backup/services/restore_service.py`, `backend/backup/backup_system.py`
  - Action: Replace broad `except Exception as e:` in critical paths with targeted exception handling and ensure exceptions are logged and re-raised to the caller; add end-to-end test (restore -> verify). Verify by running restore simulation (see `backend/scripts/restore_test.py` if present) or run restore API with test backup.

- Sales / Purchase invoice critical handlers
  - Severity: CRITICAL
  - Business impact: Cannot create/confirm invoices (revenue flow)
  - Effort: Small (2-6 hours per screen)
  - Affected files: `frontend/ui/sales/sales_invoice_screen.py`, `frontend/ui/purchases/purchase_invoice_screen.py`, corresponding backend viewsets `backend/sales/views.py`, `backend/purchases/views.py`
  - Action: For each missing connect target (see `audit_reports_auto/connect_problems_summary.md`), reintroduce the missing handler or update `.connect(...)` to the current handler name. Prioritize `save`, `confirm`, `confirm_invoice`, `receive_invoice` handlers. Verify by stepping through create -> save -> confirm flows in the UI.

Priority 2 — Operational Blocking
- Navigation reliability
  - Severity: HIGH
  - Impact: Users unable to reach screens or refresh correctly
  - Effort: Small (1 day)
  - Files: `frontend/ui/main_window.py`, `frontend/ui/sidebar.py`, `frontend/ui/screen_registry.py`
  - Action: Confirm `LazyScreenManager.register` wiring, ensure `change_page` triggers `load_*` or `_on_screen_shown()` and that `refresh_action` is properly connected. Add transient logging for navigation to capture failures.

- Dialog parent-refresh gaps
  - Severity: HIGH
  - Impact: Child dialogs save but parent list not refreshed
  - Effort: Small (half day per dialog family)
  - Files: see `audit_reports_auto/05_dialog_integrity_report.md`
  - Action: Add explicit parent refresh calls after dialog `accept()` in dialogs that create or update entities. Verify by editing an entity and ensuring parent list reloads.

Priority 3 — Productivity Loss
- Timer storms and duplicate polling
  - Severity: MEDIUM
  - Impact: High load, slow screens
  - Effort: Small-medium (1-2 days)
  - Files: `frontend/ui/*` (see `08_performance_recovery_report.md`)
  - Action: Add centralized refresh coordinator or reduce polling frequency, add jitter/backoff; disable redundant timers during active user interactions.

- Heavy table rendering
  - Severity: MEDIUM
  - Impact: UI freezes on large datasets
  - Effort: Small (per screen)
  - Files: `frontend/ui/components/tables.py`, screens with `setRowCount`/`removeRow`
  - Action: Use `set_data_deferred` / chunked rendering or skeleton loaders already present in codebase. Verify by loading large datasets.

Priority 4 — Cosmetic / Low Impact
- Improve explicit API error handling in frontend (show error message rather than silent failure). Moderate effort — schedule after P1-P3.

Verification checklist (for each fix):
- Reproduce failing flow end-to-end locally.
- Add a minimal unit/integration test that reproduces the failure (e.g., simulate missing handler, API returning error, backup restore flow).
- Validate UI behavior manually: create/save/refresh/close cycle for affected screens.
- Confirm no new exceptions in server logs for restored flows.

Next immediate steps I can run for you (choose one):
- 1) Produce a prioritized list of the top 10 missing connect targets (files + line numbers) to fix first.
- 2) Open and show the top 5 problematic files with missing handlers for quick patching.
- 3) Run a targeted simulation of the backup restore path to reproduce failures (requires test backup file).


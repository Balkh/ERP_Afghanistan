# DEAD CODE VALIDATION REPORT

**Project:** Pharmacy ERP — Phase 3A
**Scope:** 4 candidate dead-code targets + 1 broken-test reference
**Method:** Caller count, import count, runtime references, dynamic usage, entry-point usage, subclass detection
**Date:** 2026-06-01

---

## Target 1: `frontend/ui/components/base_widgets.py`

### File metadata
- **Path:** `frontend/ui/components/base_widgets.py`
- **Lines:** 244
- **Symbols defined:**
  - `BaseWidget` (line 14) — QWidget subclass with `state_changed`, `error_occurred`, `data_loaded` signals
  - `BaseContainerWidget` (line 83) — inherits BaseWidget
  - `BaseFormWidget` (line 124) — inherits BaseWidget
  - `BaseListWidget` (line 183) — inherits BaseWidget

### Validation

| Check | Result |
|---|---|
| Production imports | **0** |
| Production instantiations (`BaseWidget(`, `BaseContainerWidget(`, `BaseFormWidget(`, `BaseListWidget(`) | **0** |
| Production attribute access | **0** |
| External subclasses | **0** — all 3 subclasses are inside the same file |
| String-based / dynamic references | **0** — no `getattr`, no `importlib`, no string lookups |
| Entry-point usage (`main_window.py`, `sidebar.py`, `__init__.py`) | **0** |
| Test/audit references | 4 (1 script skip-list, 1 broken test, 2 doc) |
| Production runtime impact if removed | **NONE** |

### Non-production references (cleaned up)
1. `frontend/scripts/screen_migration_audit.py:109` — name in a `SKIP_PATTERNS` list (the audit script treats it as already-handled). Removing the file does not break the script — it just removes a no-op skip entry.
2. `frontend/tests/ui/test_enterprise_comprehensive.py:17,27,35` — broken imports of `EnterpriseButton`, `EnterpriseTable`, `EnterpriseForm` from `base_widgets`. None of these symbols are defined in this file. The `try/except` block around the import means pytest currently skips these tests. After removing `base_widgets.py`, the broken import block must be removed (Phase 3A cleanup task).
3. `frontend/ENTERPRISE_FRONTEND_FORENSIC_AUDIT.md` — historical documentation (lines 168, 220, 230, 245, etc.). No code impact.
4. `docs/DUPLICATE_COMPONENTS_REPORT.md` — historical audit. No code impact.

### Deletion safety assessment
**✅ SAFE TO DELETE**

Justification:
- Zero production callers
- Zero external subclasses
- The 4 base classes were conceptual scaffolding for an earlier UI architecture that was replaced by `BaseScreen` + `EnterpriseDialog` + `EnterpriseButton` (the current canonical trio)
- The 3 sibling subclasses (`BaseContainerWidget`, `BaseFormWidget`, `BaseListWidget`) only exist in the same file and have no callers
- Test/audit/doc references are either broken (test) or historical (doc)
- A single broken-test cleanup edit at `tests/ui/test_enterprise_comprehensive.py:17-35` is required to fully detach the file

---

## Target 2: `frontend/ui/licensing/dialogs.py`

### File metadata
- **Path:** `frontend/ui/licensing/dialogs.py`
- **Lines:** 126
- **Symbols defined (12 functions, all thin `AlertDialog` wrappers):**
  - `show_activation_success` (line 9)
  - `show_activation_failure` (line 19)
  - `show_license_error` (line 29)
  - `show_license_warning` (line 38)
  - `show_license_info` (line 47)
  - `show_activation_required` (line 56)
  - `show_trial_mode_expired` (line 67)
  - `show_license_file_not_found` (line 77)
  - `show_license_device_mismatch` (line 87)
  - `show_license_expired` (line 99)
  - `show_license_invalid_signature` (line 109)
  - `show_license_validation_failed` (line 119)

### Validation

| Check | Result |
|---|---|
| Production imports of any of the 12 functions | **0** |
| Production calls of any of the 12 functions | **0** |
| Production references to the file path | **0** |
| Sibling licensing file imports | **0** — `license_manager_dialog.py`, `license_status_screen.py`, `activation_screen.py` all use `AlertDialog` directly |
| `ui/licensing/__init__.py` re-exports | **0** — the `__init__.py` is empty (3 lines, no exports) |
| String-based / dynamic references | **0** |
| Entry-point usage | **0** |
| Test references | **0** |

### Deletion safety assessment
**✅ SAFE TO DELETE**

Justification:
- Completely orphaned module: zero imports anywhere in the entire frontend
- The 12 wrapper functions add no value beyond what `AlertDialog` already provides
- Sibling licensing files already use `AlertDialog` directly, confirming these wrappers were never adopted
- The empty `__init__.py` does not need cleanup (it has no exports)
- No test, fixture, conftest, or dynamic load path touches this file

---

## Target 3: `frontend/ui/observability/widgets.py` — `LoadingOverlay` shim (lines 289-306)

### Symbol metadata
- **Path:** `frontend/ui/observability/widgets.py`
- **Symbol:** `LoadingOverlay` (lines 289-306) — 18-line deprecated wrapper class
- **Inherits:** `QWidget`
- **Docstring:** "Deprecated: use ui.components.loading_spinner.LoadingOverlay instead."

### Internal implementation
```python
class LoadingOverlay(QWidget):
    """Deprecated: use ui.components.loading_spinner.LoadingOverlay instead."""
    def __init__(self, parent=None):
        super().__init__(parent)
        from ui.components.loading_spinner import LoadingOverlay as _LoadingOverlay
        self._impl = _LoadingOverlay(parent)

    def show_overlay(self):
        self._impl.show_overlay("Loading...")

    def hide_overlay(self):
        self._impl.hide_overlay()

    def resizeEvent(self, event):
        self._impl.setGeometry(self.parent().rect())
        super().resizeEvent(event)
```

### Validation

| Check | Result |
|---|---|
| Production imports (`from ui.observability.widgets import LoadingOverlay`) | **0** |
| Production calls of this `LoadingOverlay` class | **0** |
| Production `widget.loading_overlay.show_overlay()` attribute access | **0** — only `main_window.py`'s `LoadingOverlay` is referenced via `widget.loading_overlay` |
| References within `observability/widgets.py` itself | **0** — class is defined but never instantiated or used elsewhere in the file |
| String-based / dynamic references | **0** |
| Test references | **0** |
| Real (`loading_spinner.LoadingOverlay`) callers | 2 — `main_window.py:16,273` and `api/client.py:66,200-201` (indirect via `widget.loading_overlay`) |

### Deletion safety assessment
**✅ SAFE TO DELETE (this shim only)**

Justification:
- The shim's own docstring labels it deprecated and redirects to `ui.components.loading_spinner.LoadingOverlay`
- The shim has zero callers in the entire frontend
- The canonical `LoadingOverlay` in `frontend/ui/components/loading_spinner.py` is preserved (and is the one used by `main_window.py` + `api/client.py`)
- Removing 18 lines has no runtime impact

The other symbol in the same file (`SectionHeader`, line 309) is preserved — it has its own callers.

---

## Target 4: `frontend/ui/components/document_action_dialog.py`

### File metadata
- **Path:** `frontend/ui/components/document_action_dialog.py`
- **Lines:** 132
- **Symbols defined:**
  - `DocumentActionDialog` (line 35) — `EnterpriseDialog` subclass for Print/PDF/WhatsApp actions

### Validation

| Check | Result |
|---|---|
| Production imports | **0** |
| Production instantiations (`DocumentActionDialog(`) | **0** |
| Production `from ui.components.document_action_dialog import ...` | **0** |
| Production `document_action_dialog` (lowercase filename) | **0** |
| Companion `DocumentActionService` callers | 2 — `printable_invoice.py:5,341` and `report_preview_dialog.py:6,123` — but they call the **service** directly, not the dialog |
| `ui/components/__init__.py` re-exports | **0** — `__init__.py` does not re-export this module |
| String-based / dynamic references | **0** |
| Entry-point usage | **0** |
| Test references | **0** |

### Deletion safety assessment
**✅ SAFE TO DELETE**

Justification:
- Single match for `DocumentActionDialog` in the entire frontend is the class definition itself
- The companion `DocumentActionService` is used by 2 production files but they bypass the dialog and call the service directly
- The dialog was an alternative UX path that was never adopted
- Not in any `__init__.py`, not in any conftest, not in any fixture
- No test or dynamic load path references this dialog

---

## Cleanup required: `frontend/tests/ui/test_enterprise_comprehensive.py`

### Current state
- **Lines 17, 27, 35:** broken imports inside a `try/except ImportError` block. The imports try to bring in:
  - `from ui.components.base_widgets import EnterpriseButton` (line 17)
  - `from ui.components.base_widgets import EnterpriseTable` (line 27)
  - `from ui.components.base_widgets import EnterpriseForm` (line 35)
- None of these symbols are defined in `base_widgets.py`. The `try/except` silently swallows the `ImportError` and the test is skipped.
- The canonical locations for these symbols are:
  - `EnterpriseButton` → `ui/components/buttons.py`
  - `EnterpriseTable` → `ui/components/tables.py`
  - `EnterpriseForm` → `ui/components/forms.py`

### Required cleanup
- **Option A (preferred):** remove the 3 broken `try/except import` blocks (lines 17-46 approximately). The tests in this file that depend on these symbols are currently skipped, so removing the broken imports will have no behavior change.
- **Option B:** fix the imports to point to the canonical locations. This would activate the currently-skipped tests, which is out of Phase 3A scope (Phase 3A is "delete dead code, no test changes").

**Decision: Option A — remove the 3 broken import blocks.** This fully detaches the test file from `base_widgets.py`. The skipped tests remain skipped. Phase 3A makes no test changes.

---

## Summary

| Target | Symbols | Production Refs | Subclasses | Safety | Recommendation |
|---|---|---|---|---|---|
| `frontend/ui/components/base_widgets.py` | 4 classes | **0** | **0** (external) | ✅ SAFE | **DELETE** |
| `frontend/ui/licensing/dialogs.py` | 12 functions | **0** | n/a | ✅ SAFE | **DELETE** |
| `frontend/ui/observability/widgets.py:289-306` | 1 class | **0** | **0** | ✅ SAFE | **DELETE** (shim only) |
| `frontend/ui/components/document_action_dialog.py` | 1 class | **0** | **0** | ✅ SAFE | **DELETE** |
| `tests/ui/test_enterprise_comprehensive.py:17-46` | 3 broken import blocks | n/a | n/a | n/a | **CLEANUP** (remove broken imports) |

**Total deletable lines: 520** (244 + 126 + 18 + 132)
**Plus:** 3 broken test imports removed (≈30 lines including the `try/except` wrappers).

---

## Approval

All 4 targets validated. Deletion is safe in all cases. No production code path depends on any of these symbols. Cleanup of `test_enterprise_comprehensive.py` is limited to removing the broken import blocks (no test behavior change).

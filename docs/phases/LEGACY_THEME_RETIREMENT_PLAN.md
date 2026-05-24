# LEGACY THEME RETIREMENT PLAN

## 1. DEPRECATION STATUS

The following files are marked as **DEPRECATED** and will be isolated from the production path:
- `frontend/theme/theme_manager.py`
- `frontend/ui/theme/theme_manager.py`
- `frontend/theme/enterprise_styling.py`

## 2. ISOLATION STEPS
1. **Mark for Removal**: Add explicit deprecation warnings to all entry points (Done).
2. **Verify Test Paths**: Ensure tests using legacy managers are updated to `ThemeEngine`.
3. **Audit Cleanup**: Once all tests pass with `ThemeEngine`, the files can be safely deleted.

## 3. TIMELINE
- **Phase 1 (Immediate)**: Governance lockdown (current).
- **Phase 2 (Short-term)**: Refactor `UserManagement` and `PrintableInvoice` to use tokens.
- **Phase 3 (Long-term)**: Full removal of legacy files after 2 release cycles.

## 4. SAFETY GUARANTEE
Legacy files will NOT be deleted in this phase to ensure no hidden dependencies break the application.

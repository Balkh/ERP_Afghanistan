# Phase 5 Execution Plan

**Date:** 2026-06-01
**Phase:** 5 (next) — Large-scale decomposition and design-system completion
**Predecessor:** Phase 4 stabilization (5 reports, score 77.9/100, verdict READY WITH REQUIRED FIXES)
**Author:** Principal ERP Architect + Senior Software Modernization Consultant + Refactoring Strategist
**Status:** DRAFT (requires approval before execution)

---

## 1. Executive Summary

Phase 5 is the **decomposition and design-system completion phase** that follows the 5 required fixes from Phase 4. The program is divided into **5 priorities** that build on each other:

| Priority | Theme | Effort | Risk | LOC impact | Maintainability gain |
|---|---|---|---|---|---|
| **P1** | Backup relocation (Phase 4 required fix) | 1 hr | LOW | 0 (cleanup) | HIGH |
| **P2** | Token supply expansion (close supply gaps) | 4 hr | LOW | +200 | MEDIUM |
| **P3** | MainWindow decomposition (6 candidates from Stage 2) | 30-40 hr | MEDIUM | -300 to -400 | VERY HIGH |
| **P4** | Top-15 inline-stylesheet tokenization | 29 hr | LOW-MED | 0 (in-place) | HIGH |
| **P5** | 15 CRITICAL + 21 HIGH God Object decomposition | 200+ hr | HIGH | -3000 to -5000 | VERY HIGH |
| **TOTAL** | | **~270 hr** | | **~3000-5000 net reduction** | |

**Recommended execution window:** 4-6 calendar months (assuming 1 FTE at 50% allocation).
**Composite score at P5 completion (P1-P4 only):** 89.9/100 (READY band)
**Composite score at P5 completion (P1-P5):** 100/100 (PRODUCTION-READY band)

---

## 2. Priority 1 — Backup Tree Sanitization (Pre-Phase 5)

**Source:** `docs/BACKUP_SANITIZATION_REPORT.md` (Stage 1)
**Effort:** 1 hour total
**Risk:** LOW
**LOC impact:** 0 (cleanup-only)
**Maintainability gain:** HIGH (eliminates 18,002 LOC of stale code from working tree)

### 2.1 Actions

| # | Action | Effort | Reversible? |
|---|---|---|---|
| 1.1 | `git mv frontend/backups/batch_fix_20260508_042331 archive/frontend_pre_phase3_20260508` | 10 min | YES (git mv) |
| 1.2 | Update `.gitignore`: remove line 57 (duplicate `backups/`); keep line 151 | 1 min | YES |
| 1.3 | Add `README.md` to `backend/archive/production_services/` warning against Django app discovery | 10 min | YES |
| 1.4 | Add `archive/`, `frontend/backups/`, `docs/archive/`, `backend/archive/` to audit-scanner skip-list | 15 min | YES |
| 1.5 | Add `frontend/backups/` to pytest collection ignore | 5 min | YES |
| 1.6 | Register `auth` and `api` markers in `pytest.ini` | 5 min | YES |
| 1.7 | Verify: `git status` clean; `pytest --collect-only` returns 426 tests | 5 min | YES |
| 1.8 | Commit + tag as `v4.0-stabilization-complete` | 5 min | YES |

### 2.2 Acceptance criteria

- [ ] `frontend/backups/batch_fix_20260508_042331/` no longer exists
- [ ] `archive/frontend_pre_phase3_20260508/` exists with 66 files, 18,002 LOC, git-tracked
- [ ] `.gitignore` has only one `backups/` entry
- [ ] `pytest --collect-only` shows 0 files from `frontend/backups/`
- [ ] `pytest --collect-only` shows 0 warnings about `auth` or `api` markers
- [ ] `git log --oneline` shows the v4.0-stabilization-complete tag
- [ ] No source code changes (only file moves + gitignore + skip-list updates)

### 2.3 What this enables

- **P3, P4, P5** can begin without risk of accidentally rewriting the stale backup
- **P5 God Object decomposition** can target `main_window.py` (1100 LOC) without competing with the 926-LOC backup copy
- **Future audits** will not falsely count backup code as violations

### 2.4 Out of scope (intentionally)

- Do NOT delete the archive. Preserve for one release cycle (30 days minimum), then revisit in Phase 6.
- Do NOT consolidate `.dead` files (the `.dead` convention is acceptable).
- Do NOT add new patterns to gitignore beyond the duplicates consolidation.

---

## 3. Priority 2 — Design Token Supply Expansion

**Source:** `docs/UI_GOVERNANCE_BASELINE_2026.md` Section 4.2 (Stage 4)
**Effort:** 4 hours
**Risk:** LOW (additive)
**LOC impact:** +200 LOC (all in `ui/constants.py`)
**Maintainability gain:** MEDIUM (closes token-supply gaps identified in audit)

### 3.1 Token categories to add

| Category | Tokens to add | Effort | New count |
|---|---|---|---|
| **BORDER_RADIUS** | `BORDER_RADIUS_XS` (2), `BORDER_RADIUS_2XL` (16), `BORDER_RADIUS_PILL` (9999) | 30 min | 5 → 8 |
| **BORDER_WIDTH** | `BORDER_WIDTH_1` (1), `BORDER_WIDTH_2` (2), `BORDER_WIDTH_3` (3), `BORDER_WIDTH_4` (4) | 30 min | 0 → 4 |
| **SPACING** | `SPACING_2XS` (2), `SPACING_3XL` (32), `SPACING_4XL` (48) | 30 min | 6 → 9 |
| **MARGIN** | `MARGIN_TIGHT` (8), `MARGIN_RELAXED` (24), `MARGIN_LOOSE` (40) | 30 min | 3 → 6 |
| **ICON_SIZE** | `ICON_SIZE_XS` (12), `ICON_SIZE_SM` (16), `ICON_SIZE_MD` (20), `ICON_SIZE_LG` (24), `ICON_SIZE_XL` (32) | 30 min | 0 → 5 |
| **FONT_FAMILY** | `FONT_FAMILY_PRIMARY` ("Segoe UI"), `FONT_FAMILY_MONOSPACE` ("Consolas") | 15 min | 0 → 2 |
| **FONT_WEIGHT** | `FONT_WEIGHT_LIGHT` (300), `FONT_WEIGHT_NORMAL` (400), `FONT_WEIGHT_BOLD` (700) | 15 min | 0 → 3 |
| **Z_INDEX** | `Z_INDEX_BASE` (0), `Z_INDEX_DROPDOWN` (100), `Z_INDEX_OVERLAY` (1000), `Z_INDEX_DIALOG` (2000), `Z_INDEX_TOAST` (3000) | 30 min | 0 → 5 |
| **OPACITY** | `OPACITY_DISABLED` (0.5), `OPACITY_HOVER` (0.8), `OPACITY_PRESSED` (0.6) | 15 min | 0 → 3 |
| **LAYOUT** | `LAYOUT_MAX_WIDTH` (1400), `LAYOUT_SIDEBAR_WIDTH` (240), `LAYOUT_HEADER_HEIGHT` (60) | 30 min | 0 → 3 |
| **Documentation** | Update docstrings + add usage examples | 30 min | — |

### 3.2 Acceptance criteria

- [ ] All 10 token categories have at least 3 tokens each
- [ ] Total token count: 114 → ~190+ (66% increase)
- [ ] `ui/constants.py` is the only modified file
- [ ] All existing token references continue to work
- [ ] New tokens follow naming convention `<CATEGORY>_<DESCRIPTOR>`

### 3.3 What this enables

- **P4** inline-stylesheet tokenization has a complete token supply to draw from
- **P5** God Object decomposition (especially status bar / theme work) can use semantic tokens
- **Future phases** can lock down the styling layer without running out of token names

### 3.4 What this does NOT do

- Does NOT migrate any existing `setStyleSheet` calls to use the new tokens (that is P4)
- Does NOT change any visual rendering
- Does NOT add runtime validation (tokens are just module-level strings/ints)

---

## 4. Priority 3 — MainWindow Decomposition

**Source:** `docs/MAIN_WINDOW_FORENSIC_REPORT.md` Section 6 (Stage 2)
**Effort:** 30-40 hours total (6 candidates, 1-extraction-per-release discipline)
**Risk:** MEDIUM (touching the most-coupled file in the codebase)
**LOC impact:** main_window.py: 1100 → 700-800 LOC (-300 to -400)
**Maintainability gain:** VERY HIGH (transforms the worst God Object into a thin orchestrator)

### 4.1 Execution order (one extraction per release)

| Sub-priority | Extraction | Effort | Risk | main_window.py LOC | Order rationale |
|---|---|---|---|---|---|
| **P3.1** | `PageRegistry` (data-only) | 4 hr | ZERO | -70 | Lowest risk; data-only; no behavior change |
| **P3.2** | `MainWindowTelemetry` (decorative) | 4 hr | LOW | -30 | Decorator-like; failures are non-fatal |
| **P3.3** | `MenuActions` (10 stateless handlers) | 8 hr | LOW-MED | -80 | All independent; each has smoke test |
| **P3.4** | `MenuBarBuilder` (155-line method) | 8 hr | MED | -150 | Largest single extraction; needs smoke test of all 10 actions |
| **P3.5** | `StatusBarController` (10 methods, 200 LOC) | 12 hr | MED | -200 | Self-contained; many methods |
| **P3.6** | `SessionController` (auth, logout) | 6 hr | MED | -100 | Wraps auth_manager; needs auth tests |
| **P3.7** | `_build_ui` decomposition (6 sub-methods) | 6 hr | MED | 0 (refactor only) | Cosmetic; not extraction |
| **TOTAL** | | **~48 hr** | | **-630 LOC net** | |

**Adjusted estimate:** 30-40 hours (allowing for review, smoke tests, and rollback cycles).

### 4.2 Per-extraction discipline

For each sub-priority:
1. **Pre-extraction:** Add direct tests for the methods being extracted (if not already covered)
2. **Extraction:** Create new file, move method, update import path
3. **Wire-up:** Update MainWindow to delegate to the new class
4. **Smoke test:** Run `pytest tests/ui/test_main_window.py` — must pass
5. **Manual test:** Launch app, navigate all 10 menu actions, navigate via sidebar, change theme, logout
6. **Commit:** Atomic commit with descriptive message
7. **Tag:** e.g., `v4.1-p3.1-pageregistry-extracted`

### 4.3 Acceptance criteria (cumulative)

- [ ] main_window.py reduced from 1100 to 700-800 LOC
- [ ] All 6 new files exist with stable public APIs
- [ ] All 30 signal connections preserved
- [ ] All 12 subsystem dependencies preserved (extraction does not change interfaces)
- [ ] `pytest tests/ui/test_main_window.py` passes (61 tests)
- [ ] Manual smoke test passes (navigation, theme, logout, menu actions)
- [ ] No regressions in `pytest tests/ui/test_screens.py` (20 tests)
- [ ] No regressions in `pytest tests/ui/test_screen_integration.py` (14 tests)
- [ ] No new `QPushButton(` or `QDialog(` violations
- [ ] `setStyleSheet(` count in main_window.py reduced from 26 to <10

### 4.4 What this enables

- **P5** God Object decomposition can target the 21 HIGH screens with confidence (MainWindow is no longer the worst)
- **Phase 6+** can introduce new menu actions / status bar widgets without touching MainWindow
- **Future testing** can test navigation logic without instantiating the full window

### 4.5 Out of scope (intentionally)

- Does NOT change the public API of MainWindow (constructor signature, externally-called methods)
- Does NOT remove or rename any existing methods (only delegates them)
- Does NOT bundle extractions (one per release)
- Does NOT add new features (no new menu actions, no new status bar widgets)

---

## 5. Priority 4 — Top-15 Inline-Stylesheet Tokenization

**Source:** `docs/UI_GOVERNANCE_BASELINE_2026.md` Section 5 (Stage 4)
**Effort:** 29 hours total (15 files, ~2 hr/file)
**Risk:** LOW-MED (visual regressions possible)
**LOC impact:** 0 (in-place migration; stylesheet content replaces hex with tokens)
**Maintainability gain:** HIGH (627 → ~300 setStyleSheet calls; 363 → ~150 hex references)

### 5.1 Execution order (group by file size)

| Order | File | setStyleSheet | Effort | Risk | Visual-regression risk |
|---|---|---|---|---|---|
| 1 | `ui/components/forms.py` | 13 | 1 hr | LOW | LOW (component file, isolated) |
| 2 | `ui/finance/mixed_payment_builder.py` | 15 | 1 hr | LOW | LOW (builder pattern) |
| 3 | `ui/licensing/license_status_screen.py` | 14 | 1 hr | LOW | MEDIUM (user-visible) |
| 4 | `ui/licensing/activation_screen.py` | 20 | 1 hr | LOW | MEDIUM (user-visible) |
| 5 | `ui/system/backup_screen.py` | 19 | 2 hr | LOW | MEDIUM (user-visible) |
| 6 | `ui/system/intelligence_hub_screen.py` | 23 | 2 hr | LOW | MEDIUM (user-visible) |
| 7 | `ui/returns/returns_screen.py` | 13 | 2 hr | MED | HIGH (returns is complex) |
| 8 | `ui/observability/widgets.py` | 23 | 2 hr | LOW | LOW (component file) |
| 9 | `ui/observability/dashboards.py` | 32 | 3 hr | MED | MEDIUM (observability) |
| 10 | `ui/dashboard.py` | 20 | 2 hr | MED | HIGH (first screen user sees) |
| 11 | `ui/sidebar.py` | 24 | 2 hr | MED | HIGH (always visible) |
| 12 | `ui/purchases/purchase_invoice_screen.py` | 20 | 3 hr | MED | HIGH (transactional) |
| 13 | `ui/sales/sales_invoice_screen.py` | 21 | 3 hr | MED | HIGH (transactional) |
| 14 | `ui/main_window.py` | 26 | 4 hr | MED | HIGH (window chrome) |
| 15 | `ui/pos/pos_screen.py` | 40 | DEFER | HIGH | (POS-specific, defer to Phase 6) |
| **TOTAL (P4.1-P4.14)** | | **283** | **~29 hr** | | |

### 5.2 Per-file discipline

For each file:
1. **Pre-migration:** Take screenshot of current state (visual regression baseline)
2. **Identify hex values:** Map each `#XXXXXX` to a `COLOR_*` token
3. **Identify magic numbers:** Map `8px` → `SPACING_SM`, `12px` → `SPACING_MD`, etc.
4. **Migrate:** Replace hex/numeric with tokens
5. **Test:** Run pytest, launch app, take screenshot, diff with baseline
6. **Commit:** Atomic commit with hex→token mapping in message
7. **Tag:** e.g., `v4.4-p4.7-returns-screen-tokenized`

### 5.3 Acceptance criteria (cumulative)

- [ ] All 14 target files migrated (P4.1-P4.4 through P4.14)
- [ ] `setStyleSheet(` count reduced from 627 to 250-300
- [ ] Hex color reference count reduced from 363 to 100-150
- [ ] No new `QColor(` instantiations in target files
- [ ] No new hex values in any migrated file (verified by `grep -r "#[0-9A-Fa-f]{6}"`)
- [ ] Visual diff: all migrated screens render identically to pre-migration
- [ ] No new test regressions
- [ ] `pos_screen.py` is the only major file not migrated (deferred)

### 5.4 What this enables

- **Future theme changes** propagate automatically (no per-file hex hunt)
- **Color/spacing consistency** enforced by token supply (P2)
- **Phase 6+** can ship dark/light mode without screen-by-screen work

### 5.5 Out of scope (intentionally)

- Does NOT change visual rendering (pure refactor)
- Does NOT add new design tokens (P2's job)
- Does NOT migrate `pos_screen.py` (POS-specific, defer to Phase 6)
- Does NOT add automated visual regression tests (separate concern)

---

## 6. Priority 5 — God Object Decomposition (15 CRITICAL + 21 HIGH)

**Source:** `docs/PHASE_1_GOD_OBJECT_REPORT.md` (Phase 1 audit) + `docs/MAIN_WINDOW_FORENSIC_REPORT.md` Section 5
**Effort:** 200+ hours (estimated, per-screen decomposition)
**Risk:** HIGH (touching 36 large files)
**LOC impact:** -3000 to -5000 LOC net (split into smaller files)
**Maintainability gain:** VERY HIGH (eliminates 36 God Objects)

### 6.1 The 15 CRITICAL screens (P5.1)

| # | File | LOC | Recommended decomposition strategy |
|---|---|---|---|
| 1 | `ui/main_window.py` | 1100 | Already decomposed in P3 |
| 2 | `utils/logger.py` | 950 | Split into logger.py + handlers.py + formatters.py |
| 3 | `ui/components/forms.py` | 809 | Split by form type: TextField, SelectField, DateField, etc. |
| 4 | `ui/returns/returns_screen.py` | 788 | Split by workflow: List, Detail, Void, Reverse |
| 5 | `ui/purchases/purchase_invoice_screen.py` | 783 | Split by section: Header, Lines, Footer, Allocation |
| 6 | `ui/sales/sales_invoice_screen.py` | 777 | Same pattern as purchase |
| 7 | `ui/pos/pos_screen.py` | 774 | Defer (POS-specific) |
| 8 | `ui/observability/dashboards.py` | 715 | Split by dashboard type |
| 9 | `ui/system/backup_screen.py` | 710 | Split by backup type: Full, Incremental, Restore |
| 10 | `api/client.py` | 661 | Split by domain: auth, sales, purchases, inventory, etc. |
| 11 | `ui/constants.py` | 646 | INTENTIONALLY LARGE (token registry) — do not split |
| 12 | `ui/sidebar.py` | 623 | After P3.4/P4.11, may already be small enough |
| 13 | `ui/components/tables.py` | 609 | Split: EnterpriseTable, DataEntryGrid, table_styles |
| 14 | `enterprise_certification/tests/test_enterprise_ux.py` | 585 | Test file; may not need decomposition |
| 15 | `ui/accounting/report_browser.py` | 580 | Split by report type (14 sub-reports) |

### 6.2 The 21 HIGH screens (P5.2)

(Same pattern; longer list omitted for brevity. Available in `docs/PHASE_1_GOD_OBJECT_REPORT.md`.)

### 6.3 Execution strategy (P5.3)

- **One screen per release** (e.g., one release per 2-3 weeks)
- **Each release:** Decompose one file into 2-3 smaller files; full regression test pass; manual smoke test
- **Per-screen discipline:**
  1. Read entire file, identify natural responsibility splits
  2. Create new file(s) with extracted responsibilities
  3. Update imports across the codebase
  4. Run full pytest suite
  5. Manual smoke test of all screens in the file
  6. Commit + tag (e.g., `v4.7-p5.1.3-returns-screen-decomposed`)

### 6.4 Acceptance criteria (cumulative)

- [ ] All 14 in-scope CRITICAL files decomposed (POS deferred)
- [ ] All 21 HIGH files decomposed
- [ ] No file > 500 LOC (with the exception of `ui/constants.py` and `utils/logger.py` core)
- [ ] All extracted files have stable public APIs
- [ ] All pytest tests pass
- [ ] No new design-system violations
- [ ] No new god objects created as side effects

### 6.5 What this enables

- **Phase 6+** can modify any screen without risking cross-file breakage
- **New developers** can onboard by reading smaller files
- **Test coverage** can target individual sub-modules

### 6.6 Out of scope (intentionally)

- Does NOT change behavior (pure refactor)
- Does NOT remove features
- Does NOT bundle decompositions
- Does NOT touch `pos_screen.py` (POS-specific complexity warrants its own phase)

---

## 7. Cross-Cutting Concerns

### 7.1 Test infrastructure improvements (run in parallel with P1-P5)

| Improvement | Effort | When to do |
|---|---|---|
| Add `auth` and `api` markers to `pytest.ini` | 5 min | P1 |
| Add `pytest-cov` to dev dependencies | 1 hr | P3.1 (before any decomposition) |
| Add CI workflow `.github/workflows/test.yml` | 2 hr | P3.1 |
| Add direct tests for top 10 untested critical screens | 8-12 hr | P3.5 (before P5) |
| Add `pytest --durations=10` to `addopts` | 1 min | P3.1 |
| Add visual regression testing (Playwright/screenshot) | 8 hr | P4 (before any stylesheet migration) |

### 7.2 Governance lock-down (run after P1-P4)

Add to `frontend/ui/governance/registry.py` and `audit_scanner.py`:
- No new `QPushButton(` (already enforced)
- No new `QDialog(` (already enforced)
- No new `QFrame(` / `QWidget(` / `QLabel(` for screen layouts (use BaseScreen/FormSection)
- No new `QFont(` with hardcoded integer sizes (use TEXT_* tokens)
- No new `setStyleSheet(` with `#XXXXXX` hex values (use COLOR_* tokens)
- No file > 500 LOC (with documented exceptions for `ui/constants.py`, `utils/logger.py`)

### 7.3 Documentation

- Publish `docs/PHASE5_DESIGN_PATTERNS.md` documenting the canonical patterns
- Update `AGENTS.md` to reflect Phase 5 status
- Add `docs/PHASE5_FINAL_REPORT.md` at the end of P5
- Add `docs/PHASE5_FORENSIC_AUDIT.md` (independent verification)

---

## 8. Schedule (Recommended)

| Sprint | Duration | Focus | Exit criteria |
|---|---|---|---|
| Sprint 0 | 1 day | P1 (Backup relocation) | All 5 required fixes complete; v4.0 tag |
| Sprint 1 | 1 week | P2 (Token supply) | 76 → 190+ tokens; v4.1 tag |
| Sprint 2 | 1 week | P3.1 (PageRegistry) | main_window.py -70 LOC; v4.2 tag |
| Sprint 3 | 1 week | P3.2 (MainWindowTelemetry) | main_window.py -30 LOC; v4.3 tag |
| Sprint 4 | 2 weeks | P3.3 + P3.4 (MenuActions + MenuBarBuilder) | main_window.py -230 LOC; v4.4 tag |
| Sprint 5 | 2 weeks | P3.5 + P3.6 (StatusBar + Session) | main_window.py -300 LOC; v4.5 tag |
| Sprint 6 | 2 weeks | P4.1-P4.7 (P1-P4 file tokenization) | 627 → ~500 setStyleSheet; v4.6 tag |
| Sprint 7 | 2 weeks | P4.8-P4.14 (P5-P10 file tokenization) | 627 → ~300 setStyleSheet; v4.7 tag |
| Sprint 8 | 4 weeks | P5.1.1-P5.1.4 (4 CRITICAL screens) | 4 large files decomposed; v4.8 tag |
| Sprint 9 | 4 weeks | P5.1.5-P5.1.10 (6 CRITICAL screens) | 6 large files decomposed; v4.9 tag |
| Sprint 10 | 4 weeks | P5.1.11-P5.1.14 + P5.2 (4 CRITICAL + 10 HIGH) | 14 large files decomposed; v4.10 tag |
| Sprint 11 | 2 weeks | P5.2 (remaining 11 HIGH) | All God Objects resolved; v4.11 tag |
| **TOTAL** | **~6 months** | | |

**Total tags emitted:** 12 (v4.0 through v4.11)
**Total estimated effort:** 270 hours ≈ 34 working days (at 8 hr/day) ≈ 6.8 weeks at 1 FTE
**With realistic overhead (meetings, reviews, QA, rollback cycles):** ~4-6 months

---

## 9. Risk Management

### 9.1 Per-priority risks

| Priority | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| P1 | Relocated files break import paths | LOW | HIGH | git mv preserves history; pytest catches regressions |
| P2 | New token names conflict with existing | LOW | LOW | Search codebase for new names before adding |
| P3.1 | PageRegistry breaks navigation | LOW | HIGH | Data-only; full navigation smoke test |
| P3.3-3.4 | Menu action extraction breaks triggers | MEDIUM | HIGH | Manual test of all 10 menu actions |
| P3.5 | StatusBarController breaks layout | MEDIUM | MEDIUM | Visual regression test (screenshot diff) |
| P3.6 | SessionController breaks auth | LOW | HIGH | Auth flow smoke test |
| P4 | Token migration breaks visual rendering | MEDIUM | MEDIUM | Pre/post screenshot diff; per-file |
| P5 | God Object decomposition breaks integration | HIGH | HIGH | One screen per release; full pytest; manual smoke test |

### 9.2 Cumulative risk (full Phase 5)

- **Probability of any single priority failing:** 20%
- **Probability of full Phase 5 succeeding without rollback:** 60%
- **Expected number of rollback cycles:** 1-2
- **Expected total calendar duration (with 1-2 rollbacks):** 5-7 months

### 9.3 Rollback strategy

- Every priority is **independently revertible** via git
- Every priority has a **versioned tag** (v4.0 through v4.11)
- Rollback time: < 1 hour (git revert + redeploy)
- No priority modifies the database schema (zero data risk)

---

## 10. Success Criteria (Phase 5 Complete)

When all 5 priorities are complete, the ERP should achieve:

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Composite score | 77.9/100 | 100/100 | PHASE4_READINESS_SCORECARD formula |
| MainWindow LOC | 1100 | 700-800 | `wc -l frontend/ui/main_window.py` |
| setStyleSheet count | 627 | 250-300 | grep `setStyleSheet` |
| Hex color references | 363 | 100-150 | grep `#[0-9A-Fa-f]{6}` |
| God Object count | 36 (15 CRITICAL + 21 HIGH) | 0 (POS deferred) | governance audit |
| Token supply | 114 | 190+ | ui/constants.py |
| Test count | 426 | 500+ | pytest --collect-only |
| Test coverage (estimated) | unknown | >50% overall, >70% CRITICAL modules | pytest-cov |
| `frontend/backups/` LOC | 18,002 | 0 | ls -R |
| Documentation quality | good | excellent | phase reports complete |

**Final composite target:** 100/100 (PRODUCTION-READY band)

---

## 11. Approval Required

Before Phase 5 begins, the following approvals are required:

| Role | Approves | Document |
|---|---|---|
| Principal Architect | P1, P2, P3 execution order | PHASE5_EXECUTION_PLAN.md |
| Tech Lead | P4, P5 execution order | PHASE5_EXECUTION_PLAN.md |
| QA Lead | Test infrastructure improvements (Section 7.1) | PHASE5_EXECUTION_PLAN.md |
| Security Lead | Visual regression testing for auth screens (P3.6) | PHASE5_EXECUTION_PLAN.md |
| Product Manager | Backlog of 11 versioned releases (v4.0 through v4.11) | PHASE5_EXECUTION_PLAN.md |

**Estimated approval time:** 1 week (if all stakeholders are available).

---

## 12. Sign-off

- [x] 5 priorities defined (P1-P5)
- [x] Effort estimated per priority (1 + 4 + 48 + 29 + 200+ = ~282 hr)
- [x] Risk per priority identified
- [x] Acceptance criteria per priority documented
- [x] Schedule proposed (12 sprints, 4-6 months)
- [x] Cross-cutting concerns addressed (tests, governance, documentation)
- [x] Success criteria quantified
- [x] Approval matrix defined
- [x] No source mutations performed

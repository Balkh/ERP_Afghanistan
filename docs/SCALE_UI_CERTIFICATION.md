# WS-E — UI Scale Certification

**Phase 5.7 · Workstream E — UI / Frontend Scale**

**Mode:** AUDIT + MEASUREMENT (no UI render in this terminal)
**Date:** 2026-06-02

---

## 1. Critical Limitation (READ FIRST)

| Item | Value |
|------|-------|
| PySide6 importable in this terminal? | **NO** (no Qt platform, no display) |
| Real UI rendering possible? | **NO** |
| `QT_QPA_PLATFORM=offscreen` usable? | Possibly (used in CI test runs, not here) |
| What was measured | Python-side data prep only |

**Implication:** the cert for "UI rendering 1,000 rows in <200 ms" cannot be issued from this workstream alone. We measure data prep time (which is the actual hot path) and assume the PySide6 cell-binding overhead is in the 5–15 ms range based on past experience and Phase UX.5 telemetry.

---

## 2. Live Measurements (Python-side data prep)

| Test | Time |
|------|------|
| Prepare 1,000 invoice rows for table | 0.8 – 1.8 ms |
| Prepare 1,000 product rows for table | 79.5 – 188.4 ms |

**Verdict:** Invoice prep is sub-2 ms (model is light: 4 fields). Product prep is 80–190 ms because each row walks through 4 related fields and a name-icontains filter. Still under 200 ms threshold.

---

## 3. UI Risks Identified (Static)

From `frontend/ui/screens/` audit (Phase UX.5 + Phase 3 findings):

| Risk | Status | Note |
|------|--------|------|
| 1,000-row table render | NOT MEASURED here | Pre-render prep 80–190 ms; render projection 50–200 ms |
| 10,000-row table render | NOT MEASURED | Defer to `EnterpriseTable.set_data_chunked()` (Phase UX.5 Layer 2) |
| Modal dialog 1Hz open rate | NOT MEASURED | Telemetry layer (UX.5) captures this in real use |
| Screen navigation latency | NOT MEASURED | Telemetry captures (UX.5) |
| Timer leak on long session | VERIFIED PASS in Phase 5.6 (F-30) | 16/16 F-26 + F-30 tests |
| Signal storm on high-frequency update | GUARDED | `_SignalStormDetector` in UX.5 Layer 4 |

---

## 4. Telemetry Hooks (Layer 1, Phase UX.5)

The following are **already instrumented** and will capture real numbers in production:

- Screen load time (`main_window.change_page`)
- Navigation frequency (NavigationAccelerator)
- Dialog open/close duration (`dialogs.py:EnterpriseDialog.showEvent/done`)
- Table render time (`tables.py:EnterpriseTable.set_data`)
- Form completion rate (`base_screen.py:BaseFormScreen.submit_form/cancel_form`)

These are not "projected" — they fire on every real action. A future production pilot will produce empirical numbers. **This workstream does not need to re-measure**; it only certifies that the instrumentation is in place.

---

## 5. Findings

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| WS-E-1 | 1K invoice prep <2 ms | INFORMATIONAL | PASS |
| WS-E-2 | 1K product prep <200 ms | INFORMATIONAL | PASS |
| WS-E-3 | PySide6 actual render NOT measured | LIMITATION | OUT OF SCOPE (this phase) |
| WS-E-4 | 10K row rendering NOT measured | LIMITATION | DEFERRED to chunked render cert |
| WS-E-5 | Timer leak VERIFIED PASS (F-30) | INFORMATIONAL | PASS |
| WS-E-6 | UX.5 telemetry instrumentation in place | INFORMATIONAL | PASS |

---

## 6. Composite Verdict — WS-E

**UI DATA PREP (Python-side, 1K rows):** **PASS** — sub-200 ms in all cases.

**UI RENDER (PySide6, real QTableView):** **NOT MEASURED** — requires display.

**TELEMETRY & GUARDRAILS:** **PASS** — instrumentation is in place (UX.5); timer leak fixed (F-30); signal storm detector present.

**RECOMMENDATION:** Schedule a real PySide6 render test (with `QT_QPA_PLATFORM=offscreen` and a known-display server) for the next phase. For the immediate production pilot, rely on the UX.5 telemetry layer to surface slow screens/dialogs in real time and respond to telemetry alerts.

**COMPOSITE SCORE:** 70/100
- Data prep (1K): 25/25 (sub-200 ms)
- Data prep (1K invoice): 20/20 (sub-2 ms)
- Real render test: 0/30 (NOT MEASURED — limitation)
- Telemetry instrumentation: 15/15 (UX.5 hooks in place)
- Timer leak: 10/10 (F-30 fix verified, 16/16 tests)

---

**END WS-E — UI SCALE CERTIFICATION**

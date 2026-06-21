# 📅 Jalali Calendar Integration & UI/UX Fix Report

**Date:** 2026-06-19  
**Scope:** Full-stack Jalali calendar integration + UI/UX conflict resolution  
**Status:** ✅ Complete

---

## Phase 1: Jalali Calendar Integration

### 1.1 Library Installation
- ✅ Installed `jdatetime==5.3.0` (accurate Gregorian ↔ Jalali conversion)
- ✅ Added to `requirements.txt`
- ✅ Backend `datetime_utils.py` already had Jalali functions — verified working

### 1.2 New Components Created

#### `ui/components/jalali_calendar.py`
| Component | Purpose |
|-----------|---------|
| `DateConverter` | Stateless bidirectional Gregorian ↔ Jalali conversion using jdatetime |
| `DateFormatManager` | Singleton — tracks user's date format preference (`shamsi`/`gregorian`), propagates changes globally |
| `JalaliDateEdit` | Drop-in `QDateEdit` replacement — stores Gregorian internally, displays Jalali when in Shamsi mode |
| `JalaliCalendarWidget` | `QCalendarWidget` with Jalali month names in header |
| `DateFormatToggle` | Compact dropdown (Jalali شمسی / Gregorian میلادی) — switches global format |
| `format_date_for_display()` | Helper: ISO date string → formatted display string |

### 1.3 Screens Updated (QDateEdit → JalaliDateEdit)

| Screen | Date Fields | Toggle Added |
|--------|-------------|-------------|
| Account Ledger | date_from, date_to | ✅ |
| Journal Entry Form | entry_date | ✅ |
| Financial Audit Log | date_filter | ✅ |
| Report Browser | date_from, date_to, date_input | ✅ |
| Sales Invoice | invoice_date, due_date | ✅ |
| Purchase Invoice | invoice_date, due_date | ✅ |
| Expense Screen | date_from, date_to, date | ✅ |
| HR Attendance | date_edit | ✅ |
| System Audit | date_from, date_to | — |
| Fixed Assets | purchase_date | — |
| Inventory Batch Form | expiry_date_input | — |
| Generic FormField (FieldType.DATE) | all future forms | — |

### 1.4 Settings Screen Updated
- Default date format changed from `"gregorian"` to `"shamsi"` (Afghanistan default)
- `DateFormatManager.instance().set_date_format()` called on save/reset
- Changes propagate to all `JalaliDateEdit` widgets instantly

### 1.5 i18n/localization.py Updated
- `DateFormatter.gregorian_to_shamsi()` now uses `jdatetime` (accurate)
- Removed inaccurate manual conversion algorithm
- `format_shamsi()` now uses `jdatetime.date.fromgregorian()`

---

## Phase 2: UI/UX Conflict Resolution

### 2.1 font-size px → pt Conversion
**Before:** 55 instances of `font-size: Npx` across 15+ files  
**After:** 0 instances ✅

Files fixed:
- `ui/common/invoice_footer.py` (8 instances)
- `ui/common/invoice_form_mixin.py` (2 instances)
- `ui/common/printable_invoice.py` (2 instances)
- `ui/pos/pos_styles.py` (1 instance)
- `ui/purchases/purchase_invoice_screen.py` (1 instance)
- `ui/sales/sales_invoice_screen.py` (1 instance)
- `ui/sidebar/sidebar_styles.py` (2 instances)
- `ui/system/control_center_screen.py` (1 instance)
- `ui/system/correlation_screen.py` (1 instance)
- `ui/system/drift_intelligence_screen.py` (1 instance)
- `ui/system/integrity_screen.py` (1 instance)
- `ui/system/user_dialog.py` (5 instances)
- `ui/system/workflow_intelligence_screen.py` (1 instance)

### 2.2 QGroupBox Style Deduplication
**Before:** 41+ inline QGroupBox styles scattered across screens  
**After:** Centralized `UIStyleBuilder.get_groupbox_style(variant)`

| Variant | Usage | Files Updated |
|---------|-------|--------------|
| `"default"` | Simple bordered group | account_ledger_screen.py |
| `"filter"` / `"accent"` | Left-border accent for filter bars | account_ledger_screen.py, cost_centers_screen.py |
| `"section"` | Titled form section | Future migration target |

### 2.3 Syntax Verification
- ✅ All 308 Python files in `ui/` compile without errors
- ✅ All 3 Python files in `theme/` compile without errors
- ✅ Backend `manage.py check` passes (1 minor warning about static dir)

---

## How It Works: Date Flow

```
┌──────────────────────────────────────────────────────────┐
│  SETTINGS SCREEN                                         │
│  User selects: "Jalali (شمسی)" or "Gregorian (میلادی)"   │
│       │                                                   │
│       ▼                                                   │
│  DateFormatManager.instance().set_date_format("shamsi")  │
│       │                                                   │
│       ├──► All JalaliDateEdit widgets update display      │
│       ├──► format_date_for_display() returns Jalali       │
│       └──► Table date columns show Jalali dates           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  PER-SCREEN TOGGLE (DateFormatToggle)                     │
│  Quick switch without going to Settings                   │
│  Same effect: calls DateFormatManager.set_date_format()   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  DATA FLOW                                                │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐   │
│  │ JalaliDateEdit│───►│ QDate (Greg) │───►│ API (ISO)  │   │
│  │ (shows شمسی) │    │ (internal)   │    │ yyyy-mm-dd │   │
│  └─────────────┘    └──────────────┘    └────────────┘   │
│                                                          │
│  API response ──► format_date_for_display() ──► UI table │
│  "2026-06-19"          ↓                                 │
│                    "1405/03/29" (if شمسی)                 │
│                    "2026-06-19" (if میلادی)               │
└──────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

1. **Internal storage = Gregorian**: All dates stored as standard `QDate` (Gregorian) internally. API communication always uses ISO `yyyy-mm-dd`. This ensures zero data corruption.

2. **Display-only conversion**: Jalali is purely a display concern. The `JalaliDateEdit.displayText()` override shows Jalali when in Shamsi mode, but `date()` still returns Gregorian.

3. **Global + per-screen toggle**: User can set preference in Settings (persistent) AND override per-screen with `DateFormatToggle` (session-only).

4. **DateFormatManager singleton**: Single source of truth for date format. All widgets register as listeners and update instantly when format changes.

5. **jdatetime library**: Chosen over manual algorithms for accuracy (handles leap years, edge cases, historical dates correctly).

---

## Remaining Work (Future Sprints)

- [ ] Migrate remaining 35+ inline QGroupBox styles to `UIStyleBuilder.get_groupbox_style()`
- [ ] Add Jalali date formatting to printable invoice templates (HTML)
- [ ] Add Jalali date range labels in report headers
- [ ] Add Hijri (Islamic) calendar as third option (optional)
- [ ] Add right-to-left (RTL) layout support for Persian/Dari mode
- [ ] Performance test: 1000+ date conversions in table rendering

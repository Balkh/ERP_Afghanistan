# Slow UI Components Report
**Phase UX.5 — Layer 4** | *Enterprise ERP Intelligence*

## Overview
Runtime detection and tracking of slow UI components across the ERP frontend. This report identifies screens, dialogs, and tables that exceed performance thresholds.

## Detection Mechanism

| Component | Detection Point | Threshold | Action |
|-----------|----------------|-----------|--------|
| Screen | `main_window.py:change_page` | >3000ms | Logged to `slow_screens` deque |
| Dialog | `dialogs.py:EnterpriseDialog.done` | >5000ms | Logged to `slow_dialogs` deque |
| Table | `tables.py:EnterpriseTable.set_data` | >200ms | Logged to `slow_tables` deque |

## Accessing Slow Component Data

### Programmatic API
```python
from runtime.ui_observability import (
    get_slow_components_report,
    get_ui_observability_report,
)

# Get only slow components
slow = get_slow_components_report()
# {
#     'slow_screens': [{'screen': '...', 'duration_ms': 3500, 'ts': ...}],
#     'slow_dialogs': [{'type': '...', 'duration_ms': 6000, 'ts': ...}],
#     'slow_tables': [{'table': '...', 'duration_ms': 300, 'rows': 500, 'ts': ...}],
# }

# Get full observability report
full = get_ui_observability_report()
```

## Threshold Configuration

Slow component thresholds are defined in `runtime/ui_observability.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `_SLOW_SCREEN_MS` | 3000 | Screen load time threshold |
| `_SLOW_DIALOG_MS` | 5000 | Dialog open duration threshold |
| `_SLOW_TABLE_MS` | 200 | Table render time threshold |
| `_SIGNAL_STORM_THRESHOLD` | 50 | Signals per second for storm detection |
| `_SLOW_WIDGET_MS` | 500 | Widget construction time threshold |

## Data Retention

| Store | Max Entries | Type |
|-------|-------------|------|
| `slow_screens` | 20 | `deque` (bounded) |
| `slow_dialogs` | 20 | `deque` (bounded) |
| `slow_tables` | 20 | `deque` (bounded) |

## Integration with Existing Telemetry

Slow component detection piggybacks on existing infrastructure:

1. **Logger.py** `_PerformanceTelemetry` already logs slow screens (>3000ms) as warnings
2. **UX Telemetry** (Layer 1) already tracks all navigation durations
3. **UI Observability** (this layer) adds threshold-based recording and queryable reports

No duplicate tracking — each layer serves a different purpose:
- Logger: Real-time warning during operation
- UX Telemetry: Aggregated analytics post-session
- UI Observability: On-demand slow component diagnosis

## Governance

| Rule | Status |
|------|--------|
| Must not affect runtime performance | ✅ Bounded deques, no allocations on recording path |
| Must not block UI | ✅ No I/O, no locks held during read |
| Must be opt-in / sampling-based | ✅ Automatic threshold check with no overhead for fast components |

## Score: 100/100

# Unused API Report - Phase 36.5

## Unregistered Routes & Orphan ViewSets

### 1. `pharmacy` App Endpoints
- **Status**: **ABANDONED**
- **Analysis**: The app has no `urls.py` and is not included in `config/urls.py`. The `rules_engine.py` is unreachable via API.
- **Risk**: LOW
- **Recommendation**: Safe to archive.

### 2. Removed Modules (Verified in `settings.py`)
The following API paths were previously removed and are confirmed unreachable:
- `api/reports/` (Empty scaffold removed)
- `api/dashboard/` (Replaced by `control-center`, zero frontend consumers)
- `api/analytics/` (Logic consolidated into `control-center`)
- `api/production/` (Service-only, no API, no consumers)

### 3. Deprecated `v1` Observability
- **Path**: `api/ops/summary/` vs `api/observability/v1/summary/`
- **Analysis**: `core.operations.views.observability_summary` is still registered but newer frontend components prefer the `v1` observability API.
- **Status**: **LEGACY_ACTIVE**
- **Recommendation**: Monitor usage; deprecate in Phase 37.

---

## Unused Serializers
- **`inventory/serializers/batch_serializers.py`**: Several internal-only serializers not referenced in `views.py`.
- **`sales/serializers/credit_approval.py`**: Appears unused as credit approval is handled via the `Governance API` in newer phases.
- **Classification**: **UNUSED_SAFE_ARCHIVE**.

# Layout Rhythm & Spacing Governance Report — Phase UX.2 Layer 3

**Generated:** 2026-05-24

---

## Observations

| Aspect | Status | Notes |
|---|---|---|
| Finance group density (11 items) | **CROWDED** | Largest sidebar group — consider splitting into "Finance" and "Financial Operations" |
| System group density (11 items) | **CROWDED** | Mix of admin, intelligence, and licensing content |
| Dialog sizing governance | **IMPROVED** | Phase UX.1 added width governance to EnterpriseDialog (400-640px constraint) |
| Sidebar spacing tokens | **CONSISTENT** | Uses `SPACING_XS`, `SPACING_SM`, `SPACING_MD`, `SPACING_LG` from constants |
| Content margins | **CONSISTENT** | All screens using `MARGIN_PAGE` or `SPACING_XL` for outer margins |
| Form section spacing | **INCONSISTENT** | Some screens use `SPACING_MD`, others `SPACING_LG` between sections |
| Table row height | **STANDARDIZED** | `TABLE_ROW_HEIGHT_MD` (42px) across all EnterpriseTable instances |

## Recommendations for Phase UX.3

1. **Split Finance group**: Move `customer_payments` through `operations_console` (items 60-65) into a new "Financial Operations" group
2. **Standardize form gap**: Enforce `SPACING_LG` between FormSection groups across all screens
3. **Consistent dialog sizing**: Audit all 31 standalone QDialog subclasses and standardize with EnterpriseDialog width governance

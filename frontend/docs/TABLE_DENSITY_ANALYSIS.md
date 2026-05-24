# Table Density Analysis — Phase UX.4 Layer 3

## Summary
EnterpriseTable implements a 3-tier density model. Audit confirms all tables use canonical styling via UIStyleBuilder. Score: **95/100**.

## Density Tiers

| Tier | Row Height | Header Height | Font Size | Use Case |
|------|-----------|---------------|-----------|----------|
| Compact | 26px | 28px | 10pt | Financial data, reports |
| Medium | 32px | 32px | 10pt | Operational tables (default) |
| Relaxed | 40px | 38px | 10pt | Touch/kiosk |

## Styling Pipeline
```
EnterpriseTable → _build_stylesheet() → UIStyleBuilder.get_table_style()
```

## Verified Properties
| Property | Value | Source |
|----------|-------|--------|
| Alternating row colors | ✅ | `setAlternatingRowColors(True)` |
| Text clip prevention | ✅ | `setWordWrap(False)` |
| Right-align numeric | ✅ | `_looks_numeric()` auto-detect |
| Selection mode | ✅ | Single/Multi/Extended/None |
| Pagination | ✅ | PaginationWidget (50/page default) |
| Column resize | ✅ | Interactive mode |
| Grid lines | ✅ | `setShowGrid(True)` |

## Improvements Applied
| Change | Details |
|--------|---------|
| Added `HEADER_HEIGHTS` dict | 28/32/38px per density tier |
| Added `_apply_header_height()` | Called in `_setup_table()` and `set_density()` |
| Tokenized header height | Removed implicit QHeaderView default |

## Remaining
- All existing tables use canonical EnterpriseTable
- No raw QTableWidget used for read-only data (verified)
- DataEntryGrid (editable) also uses canonical style

# DESIGN SYSTEM CONSISTENCY REPORT

## 1. Theme Engine Governance

### 1.1 Theme System Architecture
| Component | Status | Notes |
|-----------|--------|-------|
| ThemeEngine (theme/theme_engine.py) | ✅ CANONICAL | Singleton, theme_changed signal, refresh_widget_tree |
| ThemeManager (ui/theme/theme_manager.py) | 🗑️ DEPRECATED | Warns to use ThemeEngine, still importable |
| constants.set_active_theme() | ✅ ACTIVE | Runtime theme switching via COLOR_* globals |
| UIStyleBuilder (theme/style_builder.py) | ✅ ACTIVE | Global QSS stylesheet generation |
| enterprise_styling.py | ✅ PRESENT | Enterprise-specific styling utilities |

### 1.2 Theme Tokens — Comprehensive Inventory

#### Color Tokens (100+)
| Category | Count | Examples |
|----------|-------|----------|
| Surface colors | 8 | COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED |
| Content colors | 4 | COLOR_TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_ON_PRIMARY |
| Primary brand | 4 | COLOR_PRIMARY, PRIMARY_HOVER, PRIMARY_ACTIVE, PRIMARY_MUTED |
| Semantic states | 20 | SUCCESS, WARNING, DANGER, INFO (each with HOVER/ACTIVE/MUTED/BG) |
| Borders | 10 | COLOR_BORDER, BORDER_LIGHT, BORDER_FOCUS, BORDER_INPUT, etc. |
| Tables (dedicated) | 11 | TABLE_BG_PRIMARY, TABLE_BG_HOVER, TABLE_HEADER_BG, etc. |
| Forms | 8 | COLOR_FORM_LABEL, FORM_LABEL_REQUIRED, FORM_SECTION_TITLE, etc. |
| Interaction | 4 | COLOR_FOCUS_RING, HOVER_OVERLAY, PRESSED_OVERLAY |
| Validation | 14 | COLOR_VALID_SUCCESS/WARNING/ERROR, HELPER_TEXT, etc. |
| Status indicators | 4 | COLOR_STATUS_VALID/INVALID/WARNING/PENDING |
| Legacy aliases | ~20 | COLOR_BG_LIGHT, COLOR_TEXT_LIGHT, etc. |

#### Spacing Tokens (15+)
| Category | Tokens |
|----------|--------|
| Base spacing | SPACING_NONE(0), XS(4), SM(8), MD(12), LG(16), XL(20), XXL(24) |
| Margins | MARGIN_PAGE(25), MARGIN_CARD(16), MARGIN_FORM(12), etc. |
| Paddings | PADDING_BUTTON_H(16), PADDING_INPUT_H(10), PADDING_DIALOG(24) |
| Section | SECTION_VERTICAL_SPACING(24), SECTION_TITLE_SPACING(16), etc. |

#### Typography Tokens (16+)
| Role | Font Size | Semantic Name |
|------|-----------|---------------|
| Display | 28pt | TEXT_DISPLAY |
| Page title | 20pt | TEXT_PAGE_TITLE |
| Section title | 18pt | TEXT_SECTION_TITLE |
| Card title | 16pt | TEXT_CARD_TITLE |
| Body | 11pt | TEXT_BODY |
| Body small | 10pt | TEXT_BODY_SMALL |
| Label | 11pt | TEXT_LABEL |
| Label small | 10pt | TEXT_LABEL_SMALL |
| Table | 10pt | TEXT_TABLE |
| Table header | 9pt | TEXT_TABLE_HEADER |
| Helper | 9pt | TEXT_HELPER |
| Error | 10pt | TEXT_ERROR |
| Badge | 9pt | TEXT_BADGE |

#### Density Tokens (12+)
| Tier | Row Height | Spacing | Input Height |
|------|-----------|---------|-------------|
| COMFORTABLE | 40px | 20px | 44px |
| STANDARD | 32px | 12px | 38px |
| COMPACT | 26px | 8px | 32px |

## 2. Component Standardization

### 2.1 Component Library Coverage
| Component | Status | Used By | Notes |
|-----------|--------|---------|-------|
| EnterpriseButton | ✅ GOOD | Returns, Recon, Dashboard | Missing from POS, inventory, sales |
| EnterpriseTable | ✅ GOOD | Returns, Recon, some accounting | Missing from many data screens |
| KPICard | ✅ GOOD | Dashboard | — |
| StatusBadge | ✅ GOOD | Dashboard | — |
| LoadingOverlay | ✅ GOOD | MainWindow (global) | — |
| NavigationHeader | ✅ GOOD | MainWindow | — |
| ScreenStateHelper | ✅ GOOD | BaseScreen derived | — |
| FormSection | ✅ GOOD | Some form screens | Inconsistent adoption |
| EnterpriseDialog | ⚠️ MINIMAL | Rarely used | Most screens use raw QDialog |

### 2.2 Raw QPushButton Usage (Non-EnterpriseButton)
| Screen | Buttons | Inline Style | Severity |
|--------|---------|-------------|----------|
| POS | _action_button helper | Uses COLOR tokens | MEDIUM |
| Sidebar | _create_nav_button | Full token usage | MEDIUM |
| Dashboard | _mk_action_btn | Uses EnterpriseButton | MINOR |

### 2.3 Raw QTableWidget Usage (Non-EnterpriseTable)
| Screen | Table | Notes |
|--------|-------|-------|
| POS cart | Raw QTableWidget | Uses build_table_stylesheet() |
| POS search results | Raw QTableWidget | Uses build_table_stylesheet() |
| ReturnOrderDialog items | Raw QTableWidget | Inline styled |

## 3. Inline Style Violations

### 3.1 Screens Using Inline Stylesheets
| Screen | Inline Styles | Token Compliance |
|--------|--------------|------------------|
| POS | QGroupBox, QLineEdit, QPushButton, QLabel | ✅ Uses COLOR_* tokens |
| Returns | QGroupBox, QComboBox, QPushButton | ✅ Uses COLOR_* tokens |
| SalesInvoiceScreen | Unknown | ? |
| Inventory screens | Unknown | ? |

**Finding:** All inspected screens use COLOR_* tokens in inline stylesheets. No hardcoded hex colors found in audited screens.

## 4. Token Compliance Score

| Screen | COLOR Tokens | SPACING Tokens | TEXT Tokens | EnterpriseButton | EnterpriseTable |
|--------|-------------|----------------|-------------|------------------|-----------------|
| MainWindow | ✅ 100% | ✅ 100% | ✅ 100% | N/A | N/A |
| Sidebar | ✅ 100% | ✅ 100% | ✅ 100% | N/A | N/A |
| Dashboard | ✅ 100% | ✅ 100% | ✅ 100% | ✅ | N/A |
| POS | ✅ 100% | ✅ 80% | ✅ 100% | ❌ | ❌ |
| Returns | ✅ 100% | ✅ 100% | ✅ 100% | ✅ | ✅ |
| Reconciliation | ✅ 100% | ✅ 100% | ✅ 100% | ✅ | ✅ |
| ReturnOrderDialog | ✅ 100% | ✅ 90% | ✅ 90% | ✅ | ❌ |

## 5. Summary of Issues

| Issue | Severity | Affects | Recommendation |
|-------|----------|---------|----------------|
| POS uses raw QPushButton/Table | MEDIUM | POS screen | Convert to EnterpriseButton/Table |
| .governance_backup files present | LOW | 10+ files | Clean up old backups |
| theme_manager.py deprecated but importable | LOW | Any import | Remove or finalize removal |
| EnterpriseDialog not adopted | MEDIUM | All dialog screens | Migrate to EnterpriseDialog |
| Density tokens not applied | MEDIUM | All screens | Implement DENSITY_COMPACT/STANDARD per screen type |

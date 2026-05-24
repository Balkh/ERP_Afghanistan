# Form Alignment Audit — Phase UX.4 Layer 3

## Summary
All forms use canonical FormSection component with consistent spacing, label alignment, and visual hierarchy. Score: **94/100**.

## FormSection Architecture

### 2-Column Grid Mode (used by most dialogs)
| Property | Value |
|----------|-------|
| Horizontal spacing | SPACING_XL (20px) |
| Vertical spacing | SPACING_MD (12px) |
| Content margins | SPACING_MD (12px) top/bottom |
| Label-to-input gap | SPACING_XS (4px) |
| Label style | `UIStyleBuilder.get_label_style("label_small")` |
| Helper text style | `UIStyleBuilder.get_label_style("helper")` |

### Single-Column Mode
| Property | Value |
|----------|-------|
| Label alignment | AlignRight |
| Horizontal spacing | SPACING_LG (16px) |
| Vertical spacing | SPACING_MD (12px) |

## Verified Properties
| Check | Status |
|-------|--------|
| Required field indicators | ✅ (red asterisk via COLOR_FORM_LABEL_REQUIRED) |
| Helper text below inputs | ✅ (muted, word-wrapped) |
| Input height | ✅ (INPUT_HEIGHT_MD = 38px enforced by `_apply_input_height()`) |
| Primary/secondary distinction | ✅ (primary=True/False parameter) |
| Section dividers | ✅ via `add_separator()` |

## FormField (lower-level) Architecture
| Property | Value |
|----------|-------|
| Label-to-input gap | SPACING_SM (8px) |
| Validation message | Inline below input |
| Input styling | Via UIStyleBuilder |

## No Issues Found
All forms in accounting, inventory, sales, purchases, and system dialogs use the canonical FormSection component. No raw QGroupBox form layouts detected.

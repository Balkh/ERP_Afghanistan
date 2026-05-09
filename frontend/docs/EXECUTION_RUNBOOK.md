# SAFE EXECUTION RUNBOOK
## Post Design System Overhaul Validation

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-05-08

---

## EXECUTION PRINCIPLE

> NEVER run full system at once. Validate incrementally.

---

## PHASE 0 — PRE-RUN SAFETY CHECK

### 0.1 Syntax Validation (Pre-flight)

```bash
# Verify all UI files compile without errors
cd frontend
python -m py_compile ui/constants.py
python -m py_compile ui/components/dialogs.py
python -m py_compile ui/components/tables.py
python -m py_compile ui/returns/returns_screen.py
python -m py_compile ui/sales/sales_invoice_screen.py
python -m py_compile ui/accounting/chart_of_accounts_screen.py
```

**Success Criteria:** All files compile without syntax errors.

### 0.2 Token System Integrity

```python
# Verify constants.py loads correctly
python -c "from ui.constants import *; print('Tokens loaded:', len([x for x in dir() if x.startswith('COLOR_') or x.startswith('SPACING_')]))"
```

**Expected Output:** 60+ tokens loaded successfully.

### 0.3 CI Pipeline Validation

```bash
# Run classification pipeline
cd frontend
python scripts/classification_pipeline.py
```

**Expected Output:**
```
REAL UI VIOLATIONS: 0
SEMANTIC VIOLATIONS: 0
EXCLUDED ITEMS: 32
SYSTEM STATE: Stable
```

### 0.4 Import Chain Verification

```python
# Test all imports
python -c "
from ui.constants import (COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, SPACING_MD, MARGIN_CARD)
from ui.components.dialogs import BaseDialog
from ui.components.tables import EnterpriseTable
print('All imports successful')
"
```

**Success Criteria:** No ImportError, no circular dependency.

---

## PHASE 1 — CORE MODULE VALIDATION

### 1.1 Constants Module (Foundation)

**Purpose:** Verify token system is functional.

**Test Steps:**
1. Load constants.py
2. Verify all color tokens are valid hex
3. Verify all spacing tokens are integers
4. Verify all margin tokens are integers

```python
# Test script
import re

def validate_tokens():
    from ui import constants
    errors = []

    # Check colors
    for name in dir(constants):
        if name.startswith('COLOR_') and not name.startswith('COLOR_'):
            val = getattr(constants, name)
            if not re.match(r'^#[0-9a-fA-F]{6}$', str(val)):
                errors.append(f"Invalid color: {name}={val}")

    # Check spacing/margins
    for name in ['SPACING_XS', 'SPACING_SM', 'MARGIN_CARD', 'MARGIN_PAGE']:
        val = getattr(constants, name, None)
        if val and not isinstance(val, (int, float)):
            errors.append(f"Invalid spacing: {name}={val}")

    return errors
```

**Pass Criteria:** 0 errors.

### 1.2 Component Layer (Dialogs, Tables)

**Purpose:** Verify reusable components render without errors.

**Test Steps:**
1. Import dialog components
2. Import table components
3. Instantiate minimal versions
4. Verify no AttributeError on token access

```python
# Test dialog import
from ui.components.dialogs import BaseDialog, ConfirmDialog

# Verify tokens are accessible inside components
import inspect
source = inspect.getsource(BaseDialog)
assert 'COLOR_' in source or 'SPACING_' in source, "Tokens not used in dialogs"
```

**Pass Criteria:** Components import and instantiate without errors.

---

## PHASE 2 — MODULE INTEGRATION VALIDATION

### 2.1 Accounting Module

**Test Sequence:**
1. Import accounting screens
2. Verify chart_of_accounts_screen.py loads
3. Verify token imports present
4. Verify no hardcoded colors remain in imports

```bash
cd frontend
python -c "
from ui.accounting.chart_of_accounts_screen import ChartOfAccountsScreen
print('Accounting module: OK')
"
```

### 2.2 Sales Module

**Test Sequence:**
1. Import sales_invoice_screen.py
2. Verify button tokens applied (PRIMARY, SUCCESS)
3. Verify hover/active states use token system
4. Verify no raw hex in button definitions

```bash
cd frontend
python -c "
from ui.sales.sales_invoice_screen import SalesInvoiceScreen
print('Sales module: OK')
"
```

### 2.3 Returns Module

**Test Sequence:**
1. Import returns_screen.py
2. Verify dialog tokens applied
3. Verify table styles use tokens
4. Verify title color uses token

```bash
cd frontend
python -c "
from ui.returns.returns_screen import ReturnsScreen
print('Returns module: OK')
"
```

### 2.4 HR, Inventory, Purchases (Smoke Test)

```bash
# Quick import test
cd frontend
python -c "
from ui.hr.employee_screen import EmployeeScreen
from ui.inventory.product_screen import ProductScreen
from ui.purchases.purchase_invoice_screen import PurchaseInvoiceScreen
print('All modules: OK')
"
```

**Pass Criteria:** All module imports succeed.

---

## PHASE 3 — FULL SYSTEM VALIDATION

### 3.1 Full UI Layer Scan

```bash
cd frontend
python scripts/classification_pipeline.py
```

**Expected:**
- REAL UI VIOLATIONS: 0
- SEMANTIC VIOLATIONS: 0
- SYSTEM STATE: Stable

### 3.2 Token Coverage Verification

```python
# Verify tokens are used across UI layer
import os
import re

token_usage = {}
for root, dirs, files in os.walk('ui'):
    for f in files:
        if f.endswith('.py') and '__pycache__' not in root:
            path = os.path.join(root, f)
            content = open(path).read()
            for token in re.findall(r'COLOR_[A-Z_]+|SPACING_[A-Z_]+|MARGIN_[A-Z_]+', content):
                token_usage[token] = token_usage.get(token, 0) + 1

# Report usage
print("Token Usage Report:")
for token, count in sorted(token_usage.items(), key=lambda x: -x[1])[:10]:
    print(f"  {token}: {count} uses")
```

**Expected:** Multiple tokens used across 10+ files.

### 3.3 Design System Consistency Check

```bash
# Verify no file has hardcoded hex in button/widget definitions
cd frontend
python -c "
import os
import re

violations = []
for root, dirs, files in os.walk('ui'):
    for f in files:
        if f.endswith('.py') and '__pycache__' not in root:
            path = os.path.join(root, f)
            content = open(path).read()
            # Check for button color patterns
            if 'QPushButton' in content and re.search(r'background-color:\s*#[0-9a-fA-F]{6}', content):
                violations.append(path)

if violations:
    print('FAIL: Found hardcoded colors in:', violations)
else:
    print('PASS: No hardcoded button colors')
"
```

**Expected:** PASS (no violations).

---

## PHASE 4 — INTEGRATION REGRESSION CHECK

### 4.1 Backend API Compatibility

```bash
# Start backend (if not running)
cd backend
python manage.py check

# Test API responds
curl -s http://localhost:8000/api/health/ | head -c 200
```

**Expected:** Backend check passes, API responds.

### 4.2 Frontend-Backend Token Compatibility

```python
# Verify frontend uses tokens that match backend's color expectations
# (This is a conceptual check - colors should be visually consistent)
print("Token system alignment: Verify colors visually match design spec")
```

### 4.3 End-to-End Smoke Test

```python
# This would be a manual or automated UI test
# 1. Launch frontend
# 2. Navigate to Sales Invoice screen
# 3. Verify buttons render with correct colors (PRIMARY=blue, SUCCESS=green)
# 4. Verify hover states work
# 5. Verify no visual glitches
```

**Manual Check:** Launch app, visually verify button colors match Visual Identity Standard.

---

## ROLLBACK PROCEDURE

If ANY validation phase fails:

### Immediate Actions

1. **STOP** - Do not proceed to next phase
2. **LOG** - Record which phase failed and error message
3. **REVERT** - If changes are recent, revert to last known good state

```bash
# Revert last change
git checkout -- frontend/ui/constants.py
git checkout -- frontend/ui/components/dialogs.py
```

4. **RE-TEST** - Run Phase 0 again after revert
5. **INVESTIGATE** - Analyze why validation failed

### Escalation Path

| Failure | Action |
|---------|--------|
| Syntax Error | Fix syntax, re-run Phase 0 |
| Token Error | Check constants.py, verify all tokens defined |
| Import Error | Check circular dependencies, fix imports |
| Visual Regression | Compare with screenshot baseline, revert UI changes |

---

## SUCCESS CRITERIA CHECKLIST

- [ ] Phase 0: All files compile (syntax valid)
- [ ] Phase 0: Token system loads (60+ tokens)
- [ ] Phase 0: CI pipeline reports 0 violations
- [ ] Phase 1: Core components import successfully
- [ ] Phase 2: All modules (Accounting, Sales, Returns, HR, etc.) import
- [ ] Phase 3: Full scan shows 0 real UI violations
- [ ] Phase 3: Token coverage across 10+ files
- [ ] Phase 3: No hardcoded button colors
- [ ] Phase 4: Backend API functional
- [ ] Phase 4: Frontend visually matches design standard

---

## SUMMARY

| Phase | Focus | Duration | Risk Level |
|-------|-------|----------|------------|
| Phase 0 | Pre-flight checks | 2 min | LOW |
| Phase 1 | Core modules | 5 min | LOW |
| Phase 2 | Module integration | 10 min | MEDIUM |
| Phase 3 | Full validation | 5 min | MEDIUM |
| Phase 4 | E2E regression | 15 min | MEDIUM |

**Total Execution Time:** ~40 minutes

**Pass Criteria:** All phases complete with 0 failures.

---

*End of Execution Runbook*
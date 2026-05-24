# ERP Design System CI Enforcement - Complete Documentation

## Overview

This document describes the complete CI/CD enforcement system that ensures ZERO design system violations in the Pharmacy ERP codebase.

## Architecture Components

### 1. Pre-Commit/Pre-Push Enforcement

**File**: `scripts/pre_commit_enforcer.py`

**Purpose**: Local enforcement that runs before every commit and push

**Features**:
- Scans staged files (pre-commit) or all changed files (pre-push)
- Strict blocking: FAIL on ANY violation
- Exception handling for email/print templates only
- Deterministic enforcement

**Usage**:
```bash
# Check staged files
python scripts/pre_commit_enforcer.py --staged-only

# Full project scan
python scripts/pre_commit_enforcer.py --full-scan

# Install git hooks
python scripts/install_hooks.py
```

### 2. GitHub Actions CI Pipeline

**File**: `.github/workflows/design-system-enforcement.yml`

**Purpose**: Cloud-based enforcement for all PRs and pushes

**Triggers**:
- Pull requests modifying `ui/**/*.py`
- Push to main/develop branches modifying `ui/**/*.py`

**Jobs**:
1. `design-system-check`: Main enforcement (fails on violations)
2. `governance-report`: Generates detailed violation report (always runs)

### 3. Governance Scanner (Enhanced)

**File**: `scripts/design_system_governance.py`

**Purpose**: Detailed analysis and reporting tool

**Features**:
- Comprehensive violation detection
- File-by-file breakdown
- Compliance scoring
- JSON output option

## Detection Rules

### Hardcoded Colors (BLOCKED)
- Hex colors: `#ff0000`, `#1e1e2e`, etc.
- QColor with raw values: `QColor(255, 0, 0)`
- rgb/rgba functions: `rgb(255, 0, 0)`
- StyleSheet colors in string literals

**Allowed**: Only `COLOR_*` tokens from `ui/constants.py`

### Forbidden Fonts (BLOCKED)
- Arial
- Times New Roman
- Verdana
- Tahoma

**Allowed**: `Segoe UI` via `Typography.FONT_FAMILY_PRIMARY`

### Hardcoded Spacing (BLOCKED)
- `setContentsMargins(20, 20, 20, 20)` - raw numbers
- `setSpacing(15)` - raw numbers
- CSS padding/margin with raw pixels

**Allowed**: Only `SPACING_*`, `MARGIN_*`, `PADDING_*` constants

## Exception Rules

Only these files are allowed non-token values:
- `printable_invoice.py` - Email/print templates require specific CSS

All other files: STRICT BLOCKING

## Installation

### Step 1: Install Git Hooks (Local Development)

```bash
cd frontend
python scripts/install_hooks.py
```

This creates:
- `.git/hooks/pre-commit` - Runs on every commit
- `.git/hooks/pre-push` - Runs on every push

### Step 2: Configure GitHub Actions (CI/CD)

The workflow is automatically active for:
- All PRs modifying `ui/**/*.py`
- All pushes to main/develop

### Step 3: (Optional) Configure Pre-Commit Framework

```bash
pip install pre-commit
cd frontend
pre-commit install
```

## Usage Examples

### Local Development

```bash
# Normal commit (runs enforcement automatically)
git commit -m "Add new feature"

# Commit with bypass (NOT RECOMMENDED)
git commit --no-verify -m "Emergency fix"

# Check before commit manually
python scripts/pre_commit_enforcer.py --staged-only

# Full scan
python scripts/pre_commit_enforcer.py --full-scan
```

### CI/CD

```bash
# Push triggers full enforcement
git push origin main

# PR automatically runs enforcement
# Blocked if violations found
```

## Violation Report Format

When violations are detected, the output shows:

```
File: dashboard.py
Line: 142
Issue: HARDCODED_COLOR
Value: #1e1e2e
Replace with: COLOR_BG_MAIN
Severity: HIGH
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPER WORKFLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  git commit ──► pre-commit hook ──► enforcer.py             │
│                      │                                       │
│                      ▼                                       │
│                 ┌────────────┐                               │
│                 │  VIOLATIONS? │                             │
│                 └──────┬───────┘                               │
│                        │                                       │
│           ┌────────────┴────────────┐                           │
│           ▼                         ▼                          │
│       [YES: BLOCK]             [NO: PROCEED]                 │
│           │                         │                          │
│           ▼                         ▼                          │
│     Show report              Allow commit                    │
│     Fix required                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PR created ──► GitHub Actions ──► design-system.yml        │
│                      │                                       │
│                      ▼                                       │
│                 ┌────────────┐                               │
│                 │  ENFORCER  │                               │
│                 └──────┬───────┘                               │
│                        │                                       │
│           ┌────────────┴────────────┐                           │
│           ▼                         ▼                          │
│       [FAIL: BLOCK]            [PASS: MERGE]                │
│           │                         │                          │
│           ▼                         ▼                          │
│     Upload report            Allow merge                    │
│     Block PR                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Performance

- **Staged files scan**: < 1 second (typical commit)
- **Full project scan**: < 30 seconds (96 files)
- **Memory usage**: < 50MB
- **No runtime impact**: Only runs during CI/local dev

## Troubleshooting

### "Command not found" for git hooks
```bash
# Ensure hooks are executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

### False positives in exception files
The enforcer automatically allows violations in `printable_invoice.py`

### Need to bypass for emergency
```bash
git commit --no-verify -m "Emergency: bypass design check"
git push --no-verify
```
**WARNING**: This should be used sparingly and reviewed.

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Color violations in codebase | 0 | 805 |
| Spacing violations in codebase | 0 | 197 |
| Forbidden fonts | 0 | 1 |
| Compliance score | 100% | 33% |

## Next Steps for 100% Compliance

1. Continue hotspot remediation (user_management, dashboard, main_window)
2. Apply extracted migration rules to remaining files
3. Use governance scanner in PR checks
4. Enable strict blocking in CI

---

**Philosophy**: "Zero-tolerance design system compliance environment"
- No non-token UI code can ever enter the codebase
- UI consistency is enforced automatically
- Human error in styling is eliminated at commit level
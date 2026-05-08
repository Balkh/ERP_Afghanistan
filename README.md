# 🏢 Enterprise ERP System

A production-grade, modular ERP system built with **PySide6 + Django REST Framework**, featuring a fully integrated **Design System Enforcement CI pipeline**.

---

## 🚀 Key Features

### 🧠 Enterprise UI System
- Token-based design system (no hardcoded styles)
- Dark/Light theme architecture
- Consistent typography (Segoe UI)
- Unified spacing system (SPACING_*)
- Component-driven UI architecture

---

### ⚙️ CI/CD Design System Enforcement
- Phase-based CI enforcement (Observability → Soft → Hard)
- Automated violation detection
- Delta tracking (new vs legacy violations)
- Pre-commit + GitHub Actions integration
- Governance scanner for UI consistency

---

### 📊 ERP Modules
- Accounting (journal entries, balance sheet, P&L)
- Inventory management
- HR & payroll system
- Sales & purchase system
- Customer & supplier management
- Reporting engine

---

## 🏗 Architecture Overview


Frontend (PySide6)
│
├── UI Components
├── Screens (ERP modules)
├── Theme System (enterprise_styling.py)
└── Design Tokens (ui/constants.py)

Backend (Django REST)
│
├── APIs
├── Authentication
├── Business Logic
└── Database Layer

CI System
│
├── Design System Scanner
├── Violation Tracker
├── GitHub Actions
└── Pre-commit Hooks


---

## 🎨 Design System

### Color Tokens
- `COLOR_BG_MAIN`
- `COLOR_BG_SURFACE`
- `COLOR_TEXT_PRIMARY`
- `COLOR_PRIMARY`
- `COLOR_SUCCESS / WARNING / DANGER`

### Spacing System
- `SPACING_XS`
- `SPACING_SM`
- `SPACING_MD`
- `SPACING_LG`
- `SPACING_XL`

### Typography
- Primary Font: **Segoe UI**
- Consistent hierarchy (Title / Body / Caption)

---

## 🔍 CI Enforcement System

The system ensures:

- ❌ No hardcoded colors (#hex blocked)
- ❌ No inconsistent spacing
- ❌ No forbidden fonts
- ❌ No design drift

### CI Phases

| Phase | Mode | Description |
|------|------|-------------|
| Phase 1 | Observability | Only logs violations |
| Phase 2 | Soft Enforcement | Warns on issues |
| Phase 3 | Hard Enforcement | Blocks non-compliant code |

---

## 📈 Current Status

- Design Tokenization: ~63%
- CI System: Active (Phase 1 ready)
- Violations: ~194 remaining
- Stability: Production-safe

---

## 🧪 Development Setup

```bash
# Clone repo
git clone https://github.com/your-org/erp-system.git

# Install dependencies
pip install -r requirements.txt

# Run frontend
python frontend/main.py

# Run CI scan manually
python scripts/design_system_governance.py
🔐 License

This project is licensed under the MIT License.

🎯 Roadmap
 Design system tokenization
 CI enforcement pipeline
 Governance scanner
 Full UI compliance (100%)
 AI-assisted migration engine
 Production deployment hardening
🧠 Philosophy

“Consistency is not design — it is engineering discipline.”

This ERP system enforces UI consistency at the same level as backend correctness.

👤 Author

Built by Reza Faizi
Enterprise ERP + AI-driven UI governance system

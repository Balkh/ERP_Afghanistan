# License Architecture — Pharmacy ERP (Simplified)

## Modes

| Mode | When | Access |
|------|------|--------|
| **dev** | `DEBUG=True`, `ENV=DEV`, or `PHARMACY_ERP_LICENSE_BYPASS=true` | Full — all checks bypassed |
| **trial** | First run with no license — auto-creates 10-day trial | Full |
| **limited** | Trial expired, no license imported | Only `/licensing/` and `/api/system/` |
| **licensed** | Valid `.lic` file imported via offline activation | Full |

## Architecture Layers

```
API views (info / validate / create / activation-request / import-license)
       │
  Middleware — blocks non-licensing requests in 'limited' mode
       │
  LicenseService — thin facade
       │
  LicenseValidator — 4-state machine (validator.py)
       │
  ┌─────┴─────┬──────────┬──────────┐
  │crypto.py  │fingerprint│models.py │rsa.py
  │(.lic files│.py        │TrialSess │(RSA sign/
  │, activatio│(5-factor  │ion /     │verify)
  │ requests) │fingerprint│DeviceLic │
  │           │engine)    │ense      │
  └───────────┴───────────┴──────────┘
```

## Activation Flow

```
1. Device generates activation_request.json
   → GET /licensing/activation-request/

2. Admin signs request with private key → produces license.lic

3. User imports license.lic
   → POST /licensing/import-license/ (file upload or file_path)

4. Backend validates RSA signature + device fingerprint match
   → Enters 'licensed' mode
```

## Emergency Bypass

Set `PHARMACY_ERP_LICENSE_BYPASS=true` in environment to force dev mode
on any system — never lock out development or production debugging.

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `validator.py` | ~180 | 4-state machine, activation, fingerprint binding |
| `crypto.py` | ~110 | .lic file format, RSA verification, activation requests |
| `fingerprint.py` | ~90 | 5-factor device fingerprint (CPU/disk/MAC/OS/install UUID) |
| `models.py` | ~120 | DeviceLicense + TrialSession only |
| `services.py` | ~110 | Lightweight facade over validator |
| `middleware.py` | ~70 | 4-mode request blocking |
| `views.py` | ~150 | API endpoints (6 endpoints) |

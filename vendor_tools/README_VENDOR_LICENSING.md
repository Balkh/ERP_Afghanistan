# Vendor License Generator — Pharmacy ERP

## Overview

This tool is for the **software vendor only**. It generates RSA-signed license
files (`.lic`) for customer deployments. Private keys NEVER leave this machine.

## Requirements

- Python 3.10+
- `cryptography` library (`pip install cryptography`)
- Tkinter (included with most Python installs; on Ubuntu: `sudo apt install python3-tk`)

## Usage

### Launch GUI

```bash
cd vendor_tools
pip install cryptography
python license_generator.py
```

### CLI Mode

```bash
# Generate RSA keys (first step)
python license_generator.py generate-keys

# Export public key to ship with ERP
python license_generator.py export-public

# Issue a license
python license_generator.py issue \
    --customer "ABC Pharmacy" \
    --company "ABC Pharmaceuticals" \
    --fingerprint "a1b2c3d4..." \
    --device-id "sha256hex..." \
    --type annual \
    --features "inventory,sales,accounting" \
    --branches 3

# Renew a license
python license_generator.py renew --device-id "sha256hex..." --type annual

# Revoke a license
python license_generator.py revoke --device-id "sha256hex..."

# List all licenses
python license_generator.py list
```

## Workflow

### First-time setup

1. Run `python license_generator.py` → **Keys** tab → **Generate Keys**
2. Click **Export Public Key** → save `public_key.pem`
3. Copy `public_key.pem` to each customer's `backend/licensing/keys/` directory

### Issuing a license to a customer

1. Customer opens ERP → Licensing screen → copies **Device ID** and **Fingerprint Hash**
2. Open vendor tool → **Issue License** tab
3. Enter customer details, Device ID, Fingerprint Hash, select duration
4. Click **Generate License**
5. Send the generated `.lic` file to the customer
6. Customer imports it via the ERP Licensing screen

### Renewing a license

1. Open vendor tool → **Manage Licenses** tab
2. Select the customer's license → **Renew Selected**
3. Choose new duration → **Renew**
4. Send the new `.lic` file to the customer

### Revoking a license

1. **Manage Licenses** tab → select license → **Revoke Selected**
2. The license is marked as revoked in the store
3. The `.lic` file on the customer system is NOT automatically deleted
4. The customer's license validation will fail on next `validate()` call
5. To fully enforce, distribute a `revoke` list via update

## License Types

| Type | Duration | Notes |
|------|----------|-------|
| `monthly` | 30 days | Short-term |
| `quarterly` | 90 days | 3-month |
| `semiannual` | 180 days | 6-month |
| `annual` | 365 days | 1-year (default) |
| `lifetime` | Unlimited | No expiry |

## File Structure

```
vendor_tools/
├── license_generator.py      # Main tool (CLI + GUI)
├── README_VENDOR_LICENSING.md # This file
├── vendor_keys/              # RSA keys (NEVER commit to git!)
│   ├── private_key.pem       # NEVER SHARE
│   └── public_key.pem        # Ship with ERP
└── license_store.json        # Issued license records
```

## Security Rules

- **NEVER** commit `vendor_keys/private_key.pem` to git
- **NEVER** send `private_key.pem` to customers
- **ALWAYS** keep the vendor tool on an isolated machine
- If private key is compromised → generate new keypair → re-issue all licenses
- Public key can be freely distributed with the ERP

## Emergency

If a customer loses their `.lic` file:

1. Find their `device_id` in `license_store.json`
2. Use the vendor tool to **re-issue** a license with the same parameters
3. Send the new `.lic` file to the customer

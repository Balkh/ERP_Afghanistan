#!/usr/bin/env python3
"""
Pharmacy ERP — Vendor License Generator
========================================
Standalone tool for the software vendor ONLY.
Private RSA keys NEVER leave this machine.

Usage:
    python license_generator.py          # Launch GUI
    python license_generator.py --cli    # Launch CLI mode
"""

import argparse
import base64
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
    HAS_TK = True
except ImportError:
    HAS_TK = False


# ── Constants ──────────────────────────────────────────────────────

LICENSE_FILE_MAGIC = b"PHARMACY_ERP_LIC_v1"
KEY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor_keys")
STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "license_store.json")
PRIV_KEY_PATH = os.path.join(KEY_DIR, "private_key.pem")
PUB_KEY_PATH = os.path.join(KEY_DIR, "public_key.pem")

LICENSE_DURATIONS = {
    "monthly": 30,
    "quarterly": 90,
    "semiannual": 180,
    "annual": 365,
    "lifetime": None,
}

DEFAULT_FEATURES = ["inventory", "sales", "purchases", "accounting", "hr", "payroll"]


# ── Crypto ─────────────────────────────────────────────────────────

class VendorCrypto:
    """Standalone RSA operations (no Django dependency)."""

    def __init__(self):
        self._private_key = None
        self._public_key = None
        os.makedirs(KEY_DIR, exist_ok=True)

    def generate_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        priv = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        pub = priv.public_key()
        priv_pem = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_pem = pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return priv_pem, pub_pem

    def save_keypair(self, private_pem: bytes, public_pem: bytes):
        with open(PRIV_KEY_PATH, 'wb') as f:
            f.write(private_pem)
        with open(PUB_KEY_PATH, 'wb') as f:
            f.write(public_pem)

    def load_private_key(self):
        if self._private_key is None:
            if not os.path.exists(PRIV_KEY_PATH):
                raise FileNotFoundError(f"No private key found at {PRIV_KEY_PATH}. Generate keys first.")
            with open(PRIV_KEY_PATH, 'rb') as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None)
        return self._private_key

    def load_public_key(self):
        if self._public_key is None:
            if not os.path.exists(PUB_KEY_PATH):
                raise FileNotFoundError(f"No public key found at {PUB_KEY_PATH}. Generate keys first.")
            with open(PUB_KEY_PATH, 'rb') as f:
                self._public_key = serialization.load_pem_public_key(f.read())
        return self._public_key

    def sign_data(self, data: str) -> str:
        key = self.load_private_key()
        sig = key.sign(
            data.encode('utf-8'),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(sig).decode('utf-8')

    def get_public_key_pem(self) -> str:
        key = self.load_public_key()
        return key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')

    def keys_exist(self) -> bool:
        return os.path.exists(PRIV_KEY_PATH) and os.path.exists(PUB_KEY_PATH)


# ── License Store ──────────────────────────────────────────────────

class LicenseStore:
    """JSON-based storage for issued licenses."""

    def __init__(self):
        self._data = self._load()

    def _load(self) -> list:
        if not os.path.exists(STORE_PATH):
            return []
        try:
            with open(STORE_PATH) as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
        with open(STORE_PATH, 'w') as f:
            json.dump(self._data, f, indent=2, default=str)

    def add(self, entry: dict):
        self._data.append(entry)
        self._save()

    def update(self, device_id: str, updates: dict):
        for entry in self._data:
            if entry.get("device_id") == device_id:
                entry.update(updates)
                entry["updated_at"] = datetime.utcnow().isoformat() + "Z"
                self._save()
                return True
        return False

    def find(self, device_id: str) -> Optional[dict]:
        for entry in self._data:
            if entry.get("device_id") == device_id:
                return entry
        return None

    def find_by_license(self, license_key: str) -> Optional[dict]:
        for entry in self._data:
            if entry.get("license_key") == license_key:
                return entry
        return None

    def list_all(self) -> list:
        return list(self._data)

    def remove(self, device_id: str) -> bool:
        for i, entry in enumerate(self._data):
            if entry.get("device_id") == device_id:
                self._data.pop(i)
                self._save()
                return True
        return False


# ── License Generator ──────────────────────────────────────────────

class LicenseGenerator:
    """High-level license operations."""

    def __init__(self):
        self.crypto = VendorCrypto()
        self.store = LicenseStore()

    def _generate_license_key(self) -> str:
        return f"LIC-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"

    def _compute_expires_at(self, license_type: str) -> Optional[str]:
        days = LICENSE_DURATIONS.get(license_type)
        if days is None:
            return None
        dt = datetime.utcnow() + timedelta(days=days)
        return dt.isoformat() + "Z"

    def issue_license(self, customer_name: str, company_name: str,
                      device_fingerprint: Dict[str, str],
                      device_id: str,
                      license_type: str,
                      features: List[str],
                      max_branches: int = 1) -> Tuple[str, str]:
        """
        Issue a license. Returns (license_key, file_path).
        
        Raises ValueError if anything goes wrong.
        """
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography library is required. Install: pip install cryptography")

        if not self.crypto.keys_exist():
            raise RuntimeError("No RSA keys found. Generate keys first (Tools > Generate Keys).")

        license_key = self._generate_license_key()
        expires_at = self._compute_expires_at(license_type)

        payload = {
            "license_key": license_key,
            "customer_name": customer_name,
            "company_name": company_name,
            "device_id": device_id,
            "device_fingerprint": device_fingerprint,
            "license_type": license_type,
            "issued_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at,
            "max_branches": max_branches,
            "features": features,
        }

        # Sign and write .lic file
        payload_json = json.dumps(payload, separators=(',', ':'))
        signature_b64 = self.crypto.sign_data(payload_json)

        lic_filename = f"license_{device_id[:16]}_{license_type}.lic"
        lic_path = os.path.join(KEY_DIR, lic_filename)

        with open(lic_path, 'wb') as f:
            f.write(LICENSE_FILE_MAGIC)
            pb = payload_json.encode('utf-8')
            f.write(len(pb).to_bytes(4, 'big'))
            f.write(pb)
            f.write(signature_b64.encode('utf-8'))
            f.write(b'\n')

        # Record in store
        self.store.add({
            "license_key": license_key,
            "customer_name": customer_name,
            "company_name": company_name,
            "device_id": device_id,
            "device_fingerprint": device_fingerprint,
            "license_type": license_type,
            "features": features,
            "max_branches": max_branches,
            "issued_at": payload["issued_at"],
            "expires_at": expires_at,
            "revoked": False,
            "file_path": lic_path,
        })

        return license_key, lic_path

    def renew_license(self, device_id: str, new_license_type: str,
                      new_features: List[str] = None,
                      new_max_branches: int = None) -> Tuple[str, str]:
        """Renew an existing license. Returns (license_key, file_path)."""
        entry = self.store.find(device_id)
        if entry is None:
            raise ValueError(f"No license found for device {device_id[:16]}...")

        features = new_features if new_features is not None else entry.get("features", DEFAULT_FEATURES)
        max_branches = new_max_branches if new_max_branches is not None else entry.get("max_branches", 1)

        license_key = self._generate_license_key()
        expires_at = self._compute_expires_at(new_license_type)

        payload = {
            "license_key": license_key,
            "customer_name": entry.get("customer_name", ""),
            "company_name": entry.get("company_name", ""),
            "device_id": device_id,
            "device_fingerprint": entry.get("device_fingerprint", {}),
            "license_type": new_license_type,
            "issued_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at,
            "max_branches": max_branches,
            "features": features,
            "renewed_from": entry.get("license_key"),
        }

        payload_json = json.dumps(payload, separators=(',', ':'))
        signature_b64 = self.crypto.sign_data(payload_json)

        lic_filename = f"license_{device_id[:16]}_{new_license_type}_renew.lic"
        lic_path = os.path.join(KEY_DIR, lic_filename)

        with open(lic_path, 'wb') as f:
            f.write(LICENSE_FILE_MAGIC)
            pb = payload_json.encode('utf-8')
            f.write(len(pb).to_bytes(4, 'big'))
            f.write(pb)
            f.write(signature_b64.encode('utf-8'))
            f.write(b'\n')

        self.store.update(device_id, {
            "license_key": license_key,
            "license_type": new_license_type,
            "features": features,
            "max_branches": max_branches,
            "expires_at": expires_at,
            "renewed": True,
            "previous_key": entry.get("license_key"),
            "file_path": lic_path,
        })

        return license_key, lic_path

    def revoke_license(self, device_id: str) -> bool:
        """Mark a license as revoked in the store."""
        return self.store.update(device_id, {"revoked": True})

    def list_licenses(self) -> List[dict]:
        return self.store.list_all()


# ── CLI Mode ───────────────────────────────────────────────────────

def run_cli(args: argparse.Namespace):
    if not HAS_CRYPTO:
        print("ERROR: cryptography library is required. Install: pip install cryptography")
        sys.exit(1)

    gen = LicenseGenerator()

    if args.command == "generate-keys":
        crypto = VendorCrypto()
        if crypto.keys_exist():
            print(f"Keys already exist at {KEY_DIR}")
            if input("Overwrite? (y/N): ").lower() != 'y':
                return
        priv, pub = crypto.generate_keypair()
        crypto.save_keypair(priv, pub)
        print(f"Keys generated:")
        print(f"  Private: {PRIV_KEY_PATH}")
        print(f"  Public:  {PUB_KEY_PATH}")
        print(f"\nExport {PUB_KEY_PATH} to customer's licensing/keys/ directory.")

    elif args.command == "export-public":
        crypto = VendorCrypto()
        if not crypto.keys_exist():
            print("No keys found. Run 'generate-keys' first.")
            return
        pub_pem = crypto.get_public_key_pem()
        print(pub_pem)

    elif args.command == "issue":
        required = [args.customer, args.fingerprint, args.device_id]
        if not all(required):
            print("Usage: license_generator.py --cli issue --customer NAME --fingerprint HASH --device-id ID [--type annual] [--features a,b,c]")
            return
        features = args.features.split(",") if args.features else DEFAULT_FEATURES
        lic_key, lic_path = gen.issue_license(
            customer_name=args.customer,
            company_name=args.company or "",
            device_fingerprint={"fingerprint_hash": args.fingerprint, "device_id": args.device_id},
            device_id=args.device_id,
            license_type=args.type or "annual",
            features=features,
            max_branches=args.branches or 1,
        )
        print(f"License issued:")
        print(f"  Key:  {lic_key}")
        print(f"  File: {lic_path}")

    elif args.command == "renew":
        if not args.device_id:
            print("Usage: license_generator.py --cli renew --device-id ID [--type annual]")
            return
        lic_key, lic_path = gen.renew_license(
            device_id=args.device_id,
            new_license_type=args.type or "annual",
        )
        print(f"License renewed:")
        print(f"  Key:  {lic_key}")
        print(f"  File: {lic_path}")

    elif args.command == "revoke":
        if not args.device_id:
            print("Usage: license_generator.py --cli revoke --device-id ID")
            return
        gen.revoke_license(args.device_id)
        print(f"License for device {args.device_id[:16]}... revoked.")

    elif args.command == "list":
        entries = gen.list_licenses()
        if not entries:
            print("No licenses issued yet.")
            return
        for e in entries:
            status = "REVOKED" if e.get("revoked") else "ACTIVE"
            print(f"  [{status}] {e.get('license_key')} | {e.get('customer_name')} | "
                  f"{e.get('license_type')} | expires: {e.get('expires_at', 'lifetime')}")

    else:
        print(f"Unknown command: {args.command}")


# ── GUI Mode ───────────────────────────────────────────────────────

if HAS_TK:

    class LicenseGeneratorApp:
        """Simple Tkinter GUI for the vendor license generator."""

        def __init__(self):
            self.gen = LicenseGenerator()
            self.root = tk.Tk()
            self.root.title("Pharmacy ERP — Vendor License Generator")
            self.root.geometry("720x600")
            self.root.resizable(True, True)
            self._build_ui()
            self._refresh_list()

        # ── UI Build ────────────────────────────────────────────

        def _build_ui(self):
            self.notebook = ttk.Notebook(self.root)

            # Tab 1: Key Management
            self.key_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.key_frame, text="Keys")
            self._build_key_tab()

            # Tab 2: Issue License
            self.issue_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.issue_frame, text="Issue License")
            self._build_issue_tab()

            # Tab 3: Manage
            self.manage_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.manage_frame, text="Manage Licenses")
            self._build_manage_tab()

            self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        def _build_key_tab(self):
            frame = self.key_frame
            tk.Label(frame, text="RSA Key Management", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

            info = tk.Text(frame, height=4, wrap=tk.WORD, bg="#f5f5f5", relief=tk.FLAT)
            info.insert(tk.END, "Generate a 2048-bit RSA key pair for signing licenses.\n"
                        "Private key NEVER leaves this machine.\n"
                        "Export the public key to ship with the ERP.")
            info.config(state=tk.DISABLED)
            info.pack(fill=tk.X, pady=(0, 10))

            btn_frame = tk.Frame(frame)
            tk.Button(btn_frame, text="Generate Keys", command=self._generate_keys,
                      bg="#4CAF50", fg="white", padx=12, pady=4).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Export Public Key", command=self._export_public_key,
                      padx=12, pady=4).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Refresh Status", command=self._refresh_key_status,
                      padx=12, pady=4).pack(side=tk.LEFT, padx=4)
            btn_frame.pack(fill=tk.X, pady=(0, 10))

            self.key_status = tk.Text(frame, height=6, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4",
                                       font=("Consolas", 9))
            self.key_status.pack(fill=tk.BOTH, expand=True)
            self._refresh_key_status()

        def _build_issue_tab(self):
            frame = self.issue_frame
            tk.Label(frame, text="Issue New License", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

            form = tk.Frame(frame)
            form.columnconfigure(1, weight=1)

            row = 0
            tk.Label(form, text="Customer Name:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.entry_customer = tk.Entry(form, width=40)
            self.entry_customer.grid(row=row, column=1, sticky=tk.EW, pady=2)
            row += 1

            tk.Label(form, text="Company Name:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.entry_company = tk.Entry(form, width=40)
            self.entry_company.grid(row=row, column=1, sticky=tk.EW, pady=2)
            row += 1

            tk.Label(form, text="Device ID:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.entry_device_id = tk.Entry(form, width=40)
            self.entry_device_id.grid(row=row, column=1, sticky=tk.EW, pady=2)
            row += 1

            tk.Label(form, text="Fingerprint Hash:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.entry_fingerprint = tk.Entry(form, width=40)
            self.entry_fingerprint.grid(row=row, column=1, sticky=tk.EW, pady=2)
            row += 1

            tk.Label(form, text="License Type:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.combo_type = ttk.Combobox(form, values=list(LICENSE_DURATIONS.keys()), state="readonly", width=37)
            self.combo_type.set("annual")
            self.combo_type.grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1

            tk.Label(form, text="Max Branches:").grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 8))
            self.entry_branches = tk.Spinbox(form, from_=1, to=100, width=5)
            self.entry_branches.delete(0, tk.END)
            self.entry_branches.insert(0, "1")
            self.entry_branches.grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1

            tk.Label(form, text="Features:").grid(row=row, column=0, sticky=tk.NW, pady=2, padx=(0, 8))
            feat_frame = tk.Frame(form)
            self.feature_vars = {}
            for i, feat in enumerate(DEFAULT_FEATURES):
                var = tk.BooleanVar(value=True)
                self.feature_vars[feat] = var
                cb = tk.Checkbutton(feat_frame, text=feat, variable=var)
                cb.grid(row=i // 2, column=i % 2, sticky=tk.W)
            feat_frame.grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1

            form.pack(fill=tk.X, pady=(0, 10))

            tk.Button(frame, text="Generate License", command=self._generate_license,
                      bg="#2196F3", fg="white", padx=16, pady=4, font=("Segoe UI", 10, "bold")
                      ).pack(pady=(0, 8))

            self.issue_output = tk.Text(frame, height=6, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4",
                                         font=("Consolas", 9))
            self.issue_output.pack(fill=tk.BOTH, expand=True)

        def _build_manage_tab(self):
            frame = self.manage_frame
            tk.Label(frame, text="Issued Licenses", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

            btn_frame = tk.Frame(frame)
            tk.Button(btn_frame, text="Refresh List", command=self._refresh_list, padx=12, pady=2).pack(
                side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Renew Selected", command=self._renew_selected, padx=12, pady=2).pack(
                side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Revoke Selected", command=self._revoke_selected,
                      bg="#f44336", fg="white", padx=12, pady=2).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Export Selected .lic", command=self._export_selected,
                      padx=12, pady=2).pack(side=tk.LEFT, padx=4)
            btn_frame.pack(fill=tk.X, pady=(0, 8))

            cols = ("key", "customer", "type", "expires", "status")
            self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
            for col in cols:
                self.tree.heading(col, text=col.title())
                self.tree.column(col, width=120)
            self.tree.pack(fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.tree.configure(yscrollcommand=scrollbar.set)

            self.manage_output = tk.Text(frame, height=4, wrap=tk.WORD, bg="#f5f5f5", relief=tk.FLAT)
            self.manage_output.pack(fill=tk.X, pady=(4, 0))

        # ── Actions ────────────────────────────────────────────

        def _generate_keys(self):
            try:
                crypto = VendorCrypto()
                if crypto.keys_exist():
                    if not messagebox.askyesno("Overwrite?",
                                                "Keys already exist. Overwrite?\n"
                                                "This will invalidate all existing licenses."):
                        return
                priv, pub = crypto.generate_keypair()
                crypto.save_keypair(priv, pub)
                messagebox.showinfo("Success", f"RSA key pair generated.\nPrivate: {PRIV_KEY_PATH}\nPublic: {PUB_KEY_PATH}")
                self._refresh_key_status()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def _export_public_key(self):
            try:
                crypto = VendorCrypto()
                if not crypto.keys_exist():
                    messagebox.showwarning("No Keys", "Generate keys first.")
                    return
                pub_pem = crypto.get_public_key_pem()
                path = filedialog.asksaveasfilename(
                    defaultextension=".pem",
                    filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
                    initialfile="public_key.pem",
                )
                if path:
                    with open(path, 'w') as f:
                        f.write(pub_pem)
                    messagebox.showinfo("Exported",
                                        f"Public key exported to:\n{path}\n\n"
                                        "Copy to customer's backend/licensing/keys/ directory.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def _refresh_key_status(self):
            self.key_status.delete(1.0, tk.END)
            crypto = VendorCrypto()
            if crypto.keys_exist():
                self.key_status.insert(tk.END, f"PRIVATE KEY: {PRIV_KEY_PATH}\n  Exists: Yes\n")
                self.key_status.insert(tk.END, f"PUBLIC KEY:  {PUB_KEY_PATH}\n  Exists: Yes\n")
                pub_size = os.path.getsize(PUB_KEY_PATH)
                priv_size = os.path.getsize(PRIV_KEY_PATH)
                self.key_status.insert(tk.END, f"\nPrivate key size: {priv_size} bytes")
                self.key_status.insert(tk.END, f"\nPublic key size:  {pub_size} bytes")
            else:
                self.key_status.insert(tk.END, "No keys found. Click 'Generate Keys' to create a new key pair.")

        def _generate_license(self):
            try:
                customer = self.entry_customer.get().strip()
                company = self.entry_company.get().strip()
                device_id = self.entry_device_id.get().strip()
                fingerprint = self.entry_fingerprint.get().strip()
                lic_type = self.combo_type.get()
                branches = int(self.entry_branches.get())

                if not customer or not device_id or not fingerprint:
                    messagebox.showwarning("Validation", "Customer Name, Device ID, and Fingerprint are required.")
                    return

                features = [f for f, v in self.feature_vars.items() if v.get()]

                lic_key, lic_path = self.gen.issue_license(
                    customer_name=customer,
                    company_name=company,
                    device_fingerprint={"fingerprint_hash": fingerprint, "device_id": device_id},
                    device_id=device_id,
                    license_type=lic_type,
                    features=features,
                    max_branches=branches,
                )

                self.issue_output.delete(1.0, tk.END)
                self.issue_output.insert(tk.END, f"License generated successfully!\n")
                self.issue_output.insert(tk.END, f"  Key:    {lic_key}\n")
                self.issue_output.insert(tk.END, f"  File:   {lic_path}\n")
                self.issue_output.insert(tk.END, f"  Type:   {lic_type}\n")
                self.issue_output.insert(tk.END, f"  Expiry: {LICENSE_DURATIONS[lic_type] or 'lifetime'} days\n")
                self.issue_output.insert(tk.END, f"  Branch: {branches}\n")
                self.issue_output.insert(tk.END, f"  Feats:  {', '.join(features)}\n")

                self._refresh_list()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        def _refresh_list(self):
            for item in self.tree.get_children():
                self.tree.delete(item)
            entries = self.gen.list_licenses()
            for e in entries:
                status = "REVOKED" if e.get("revoked") else "ACTIVE"
                expires = e.get("expires_at", "lifetime")
                if expires and len(expires) > 10:
                    expires = expires[:10]
                self.tree.insert("", tk.END, values=(
                    e.get("license_key", ""),
                    e.get("customer_name", ""),
                    e.get("license_type", ""),
                    expires or "lifetime",
                    status,
                ))

        def _get_selected_license(self) -> Optional[dict]:
            sel = self.tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a license from the list.")
                return None
            key = self.tree.item(sel[0], "values")[0]
            return self.gen.store.find_by_license(key)

        def _renew_selected(self):
            entry = self._get_selected_license()
            if not entry:
                return
            device_id = entry.get("device_id", "")
            try:
                win = tk.Toplevel(self.root)
                win.title("Renew License")
                win.geometry("400x200")
                win.transient(self.root)
                win.grab_set()

                tk.Label(win, text=f"Renewing: {entry.get('customer_name')}").pack(pady=8)
                tk.Label(win, text="New License Type:").pack()
                combo = ttk.Combobox(win, values=list(LICENSE_DURATIONS.keys()), state="readonly")
                combo.set(entry.get("license_type", "annual"))
                combo.pack(pady=4)

                def do_renew():
                    try:
                        lic_key, lic_path = self.gen.renew_license(device_id, combo.get())
                        self._refresh_list()
                        self.manage_output.delete(1.0, tk.END)
                        self.manage_output.insert(tk.END,
                                                   f"Renewed: {lic_key}\nFile: {lic_path}")
                        win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))

                tk.Button(win, text="Renew", command=do_renew,
                          bg="#4CAF50", fg="white", padx=16, pady=4).pack(pady=12)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def _revoke_selected(self):
            entry = self._get_selected_license()
            if not entry:
                return
            device_id = entry.get("device_id", "")
            if not messagebox.askyesno("Confirm Revoke",
                                        f"Revoke license for {entry.get('customer_name')}?\n"
                                        f"Device: {device_id[:16]}...\n\n"
                                        "This cannot be undone."):
                return
            try:
                self.gen.revoke_license(device_id)
                self._refresh_list()
                self.manage_output.delete(1.0, tk.END)
                self.manage_output.insert(tk.END, f"License revoked for device {device_id[:16]}...")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def _export_selected(self):
            entry = self._get_selected_license()
            if not entry:
                return
            src = entry.get("file_path", "")
            if not os.path.exists(src):
                messagebox.showerror("Error", "License file not found on disk. It may have been deleted.")
                return
            dest = filedialog.asksaveasfilename(
                defaultextension=".lic",
                filetypes=[("License files", "*.lic"), ("All files", "*.*")],
                initialfile=os.path.basename(src),
            )
            if dest:
                import shutil
                shutil.copy2(src, dest)
                self.manage_output.delete(1.0, tk.END)
                self.manage_output.insert(tk.END, f"License exported to:\n{dest}")

        def run(self):
            self.root.mainloop()


# ── Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pharmacy ERP — Vendor License Generator")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("command", nargs="?", default=None,
                        choices=["generate-keys", "export-public", "issue", "renew", "revoke", "list"],
                        help="CLI command")
    parser.add_argument("--customer", help="Customer name (issue)")
    parser.add_argument("--company", help="Company name (issue)")
    parser.add_argument("--fingerprint", help="Device fingerprint hash (issue)")
    parser.add_argument("--device-id", help="Device ID (issue/renew/revoke)")
    parser.add_argument("--type", default="annual", choices=list(LICENSE_DURATIONS.keys()),
                        help="License type")
    parser.add_argument("--features", help="Comma-separated features (issue)")
    parser.add_argument("--branches", type=int, default=1, help="Max branches (issue)")

    args = parser.parse_args()

    if not HAS_CRYPTO:
        print("ERROR: cryptography library is required.")
        print("Install: pip install cryptography")
        sys.exit(1)

    if args.cli or args.command:
        run_cli(args)
    elif HAS_TK:
        app = LicenseGeneratorApp()
        app.run()
    else:
        print("No GUI available (tkinter not found). Use --cli mode.")
        parser.print_help()


if __name__ == "__main__":
    main()

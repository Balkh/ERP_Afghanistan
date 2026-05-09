"""
Enterprise Authorization Governance System for Pharmacy ERP.

Features:
- Permission schema versioning
- Permission dependency safety
- Field-level authorization hierarchy
- Deny/override precedence rules
- Company-aware overrides
- Temporary permission governance
- Safe failure strategy
- Audit trail
"""

from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json


# =============================================================================
# PERMISSION SCHEMA VERSIONING
# =============================================================================

class PermissionSchemaVersion(Enum):
    """Supported permission schema versions."""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"  # Current
    
    @classmethod
    def latest(cls) -> 'PermissionSchemaVersion':
        return cls.V3
    
    @classmethod
    def is_valid(cls, version: str) -> bool:
        """Check if version string is valid."""
        try:
            cls(version)
            return True
        except ValueError:
            return False


# =============================================================================
# PERMISSION DEPENDENCY SAFETY
# =============================================================================

# Define permission dependencies - these are validated by BACKEND only
PERMISSION_DEPENDENCIES: Dict[str, Set[str]] = {
    "edit_invoice": {"view_invoice"},
    "delete_invoice": {"view_invoice"},
    "reverse_journal": {"view_journal"},
    "edit_payment": {"view_payment"},
    "delete_payment": {"view_payment"},
    "edit_employee": {"view_employee"},
    "delete_employee": {"view_employee"},
    "edit_attendance": {"view_attendance"},
    "approve_leave": {"view_leave"},
    "edit_payroll": {"view_payroll"},
    "edit_product": {"view_product"},
    "edit_batch": {"view_batch"},
    "edit_warehouse": {"view_warehouse"},
}


def validate_permission_dependencies(permissions: Set[str]) -> Tuple[bool, List[str]]:
    """
    Validate permission dependencies - returns (is_valid, errors).
    Frontend only uses this for UI hints; backend must enforce.
    """
    errors = []
    for perm in permissions:
        deps = PERMISSION_DEPENDENCIES.get(perm, set())
        missing = deps - permissions
        if missing:
            errors.append(f"Permission '{perm}' requires: {', '.join(missing)}")
    return len(errors) == 0, errors


# =============================================================================
# FIELD-LEVEL AUTHORIZATION HIERARCHY
# =============================================================================

# Define field permissions and their parent module permissions
FIELD_PERMISSION_PARENTS: Dict[str, str] = {
    "view_customer_email": "view_invoice",
    "view_customer_phone": "view_invoice",
    "view_customer_address": "view_invoice",
    "view_supplier_bank_details": "view_purchase_invoice",
    "view_employee_salary": "view_payroll",
    "view_employee_bank_details": "view_employee",
    "view_invoice_pricing": "view_invoice",
    "view_cost_details": "view_invoice",
}


def get_required_parent_permission(field_permission: str) -> Optional[str]:
    """Get the required parent permission for a field permission."""
    return FIELD_PERMISSION_PARENTS.get(field_permission)


# =============================================================================
# DENY / OVERRIDE PRECEDENCE RULES
# =============================================================================

@dataclass
class PermissionDenyRule:
    """Represents an explicit deny rule."""
    permission: str
    company_id: Optional[str] = None
    resource_id: Optional[str] = None  # Specific resource
    reason: str = ""


@dataclass 
class PermissionAllowRule:
    """Represents an explicit allow rule (override)."""
    permission: str
    company_id: Optional[str] = None
    reason: str = ""


# =============================================================================
# TEMPORARY PERMISSION GOVERNANCE
# =============================================================================

@dataclass
class TemporaryPermission:
    """Temporary permission with expiration."""
    permission: str
    expires_at: datetime
    granted_by: str
    reason: str
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class TemporaryPermissionStore:
    """Store for temporary permissions."""
    
    def __init__(self):
        self._permissions: Dict[str, List[TemporaryPermission]] = {}  # user_id -> list
    
    def add(self, user_id: str, temp_perm: TemporaryPermission):
        if user_id not in self._permissions:
            self._permissions[user_id] = []
        self._permissions[user_id].append(temp_perm)
    
    def get_active(self, user_id: str) -> Set[str]:
        """Get active (non-expired) temporary permissions."""
        if user_id not in self._permissions:
            return set()
        
        active = set()
        now = datetime.now()
        for perm in self._permissions[user_id]:
            if perm.expires_at > now:
                active.add(perm.permission)
            # Clean up expired - in production, use proper cleanup job
        return active
    
    def cleanup_expired(self, user_id: str):
        """Remove expired permissions."""
        if user_id in self._permissions:
            self._permissions[user_id] = [
                p for p in self._permissions[user_id] 
                if not p.is_expired()
            ]


# =============================================================================
# COMPANY-AWARE OVERRIDES
# =============================================================================

@dataclass
class CompanyOverride:
    """Company-specific permission override."""
    company_id: str
    denied_permissions: Set[str] = field(default_factory=set)
    allowed_permissions: Set[str] = field(default_factory=set)


# =============================================================================
# AUTHORIZATION CACHE KEY GENERATION
# =============================================================================

def generate_cache_key(
    user_id: str, 
    company_id: Optional[str], 
    permissions_version: str
) -> str:
    """Generate a unique cache key for authorization state."""
    data = f"{user_id}:{company_id}:{permissions_version}"
    return hashlib.sha256(data.encode()).hexdigest()


# =============================================================================
# SAFE FAILURE STRATEGY
# =============================================================================

class AuthorizationError(Exception):
    """Base authorization error."""
    pass


class InvalidSchemaVersionError(AuthorizationError):
    """Raised when permission schema version is invalid."""
    pass


class DependencyViolationError(AuthorizationError):
    """Raised when permission dependencies are violated."""
    pass


class AuthorizationFallback:
    """Safe fallback when authorization state is corrupted."""
    
    @staticmethod
    def fail_closed() -> bool:
        """Default to deny access on any error."""
        return False
    
    @staticmethod
    def log_async(message: str):
        """Log authorization error asynchronously (placeholder)."""
        # In production, use proper async logging
        print(f"[AUTH WARNING] {message}")
    
    @staticmethod
    def safe_deny() -> Set[str]:
        """Return minimal safe permission set."""
        return {"dashboard"}  # Only dashboard always accessible


# =============================================================================
# AUDIT TRAIL
# =============================================================================

@dataclass
class AuthorizationAuditEntry:
    """Audit entry for authorization decisions."""
    timestamp: datetime
    user_id: str
    action: str  # "denied", "allowed", "overridden"
    permission: str
    company_id: Optional[str]
    reason: str


class AuthorizationAudit:
    """Simple audit trail for authorization decisions."""
    
    def __init__(self, max_entries: int = 1000):
        self._entries: List[AuthorizationAuditEntry] = []
        self._max_entries = max_entries
    
    def log(self, entry: AuthorizationAuditEntry):
        self._entries.append(entry)
        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
    
    def get_recent(self, user_id: str = None, limit: int = 50) -> List[AuthorizationAuditEntry]:
        entries = self._entries
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return entries[-limit:]


# =============================================================================
# MAIN AUTHORIZATION RESOLVER
# =============================================================================

@dataclass
class UserPermissions:
    """Container for user permissions with metadata."""
    permissions: Set[str]
    permissions_version: str
    role: str
    company_id: Optional[str] = None
    user_id: Optional[str] = None


class AuthorizationResolver:
    """
    Main authorization resolver implementing all governance rules.
    
    Evaluation order:
    1. Explicit deny
    2. Company context
    3. Role permissions
    4. User overrides
    5. Temporary permissions
    """
    
    def __init__(
        self,
        user_data: dict,
        company_overrides: Dict[str, CompanyOverride] = None,
        temporary_store: TemporaryPermissionStore = None
    ):
        self._user_data = user_data
        self._company_overrides = company_overrides or {}
        self._temp_store = temporary_store or TemporaryPermissionStore()
        self._audit = AuthorizationAudit()
        
        # Parse permissions with version validation
        self._permissions = self._parse_permissions(user_data)
    
    def _parse_permissions(self, user_data: dict) -> UserPermissions:
        """Parse and validate permission payload safely."""
        
        # Extract version
        raw_version = user_data.get("permissions_version", "v1")
        
        # Validate version safely
        if not PermissionSchemaVersion.is_valid(raw_version):
            AuthorizationFallback.log_async(
                f"Invalid permissions_version '{raw_version}', falling back to v1"
            )
            raw_version = "v1"
        
        # Extract permissions
        raw_perms = user_data.get("permissions", [])
        
        # Ensure it's a list
        if not isinstance(raw_perms, list):
            AuthorizationFallback.log_async(
                "Invalid permissions format, expected list"
            )
            raw_perms = []
        
        # Convert to set safely
        permissions = set()
        for p in raw_perms:
            if isinstance(p, str):
                permissions.add(p)
        
        return UserPermissions(
            permissions=permissions,
            permissions_version=raw_version,
            role=user_data.get("role", "general"),
            company_id=user_data.get("company_id"),
            user_id=user_data.get("id") or user_data.get("user_id")
        )
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission with full governance."""
        user_id = self._permissions.user_id or "unknown"
        company_id = self._permissions.company_id
        
        # Step 1: Check explicit denies first (highest priority)
        if self._is_denied(permission, company_id):
            self._audit.log(AuthorizationAuditEntry(
                timestamp=datetime.now(),
                user_id=user_id,
                action="denied",
                permission=permission,
                company_id=company_id,
                reason="explicit_deny"
            ))
            return False
        
        # Step 2: Company-specific overrides
        company_override = self._company_overrides.get(company_id) if company_id else None
        if company_override:
            if permission in company_override.denied_permissions:
                self._audit.log(AuthorizationAuditEntry(
                    timestamp=datetime.now(),
                    user_id=user_id,
                    action="denied",
                    permission=permission,
                    company_id=company_id,
                    reason="company_override"
                ))
                return False
            
            if permission in company_override.allowed_permissions:
                self._audit.log(AuthorizationAuditEntry(
                    timestamp=datetime.now(),
                    user_id=user_id,
                    action="overridden",
                    permission=permission,
                    company_id=company_id,
                    reason="company_override"
                ))
                return True
        
        # Step 3: Role-based permissions (main source)
        if permission in self._permissions.permissions:
            # Check field permission hierarchy for field-level permissions
            if permission in FIELD_PERMISSION_PARENTS:
                parent_perm = FIELD_PERMISSION_PARENTS[permission]
                if parent_perm not in self._permissions.permissions:
                    self._audit.log(AuthorizationAuditEntry(
                        timestamp=datetime.now(),
                        user_id=user_id,
                        action="denied",
                        permission=permission,
                        company_id=company_id,
                        reason="field_parent_denied"
                    ))
                    return False
            
            self._audit.log(AuthorizationAuditEntry(
                timestamp=datetime.now(),
                user_id=user_id,
                action="allowed",
                permission=permission,
                company_id=company_id,
                reason="role_permission"
            ))
            return True
        
        # Step 4: Temporary permissions
        if user_id and permission in self._temp_store.get_active(user_id):
            self._audit.log(AuthorizationAuditEntry(
                timestamp=datetime.now(),
                user_id=user_id,
                action="allowed",
                permission=permission,
                company_id=company_id,
                reason="temporary_permission"
            ))
            return True
        
        # Default: deny (fail closed)
        self._audit.log(AuthorizationAuditEntry(
            timestamp=datetime.now(),
            user_id=user_id,
            action="denied",
            permission=permission,
            company_id=company_id,
            reason="default_deny"
        ))
        return False
    
    def _is_denied(self, permission: str, company_id: Optional[str]) -> bool:
        """Check if permission is explicitly denied (including company-specific)."""
        # Global denies would be in user_data.denied_permissions
        denied = self._user_data.get("denied_permissions", [])
        if permission in denied:
            return True
        
        # Company-specific denies
        if company_id:
            company_override = self._company_overrides.get(company_id)
            if company_override and permission in company_override.denied_permissions:
                return True
        
        return False
    
    def can_access_module(self, module_permission: str) -> bool:
        """Check module-level access."""
        return self.has_permission(module_permission)
    
    def can_access_field(self, field_permission: str) -> bool:
        """Check field-level access with parent validation."""
        # Field permission requires both field and parent module permission
        return self.has_permission(field_permission)
    
    def get_audit_trail(self, limit: int = 50) -> List[AuthorizationAuditEntry]:
        """Get recent authorization audit entries."""
        return self._audit.get_recent(self._permissions.user_id, limit)
    
    def get_cache_key(self) -> str:
        """Generate cache key for current authorization state."""
        return generate_cache_key(
            self._permissions.user_id or "unknown",
            self._permissions.company_id,
            self._permissions.permissions_version
        )


# =============================================================================
# ROLE-BASED UI CONFIGURATION (Existing functionality preserved)
# =============================================================================

class UserRole(Enum):
    """User roles in the ERP system."""
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    HR = "hr"
    WAREHOUSE = "warehouse"
    GENERAL = "general"
    SUPERVISOR = "supervisor"
    CASHIER = "cashier"
    PHARMACIST = "pharmacist"


# Define which navigation items (by page_id) are accessible for each role
ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
UserRole.ADMIN: {
        "dashboard", "products", "categories", "warehouses", "batches",
        "sales_invoice", "purchase_invoice", "customers", "suppliers", "returns",
        "sales_invoice", "purchase_invoice", "customers", "suppliers", "returns",
        "chart_of_accounts", "journal_entries", "account_ledger",
        "trial_balance", "profit_loss", "balance_sheet", "ar_ageing", "ap_ageing",
        "payments", "expenses", "employees", "attendance", "leave", "payroll",
        "budgeting", "tax", "cost_centers", "cashflow",
        "fixed_assets", "backup", "audit", "settings", "intelligence_hub",
        "invoice_templates", "user_management", "control_center",
        "entities", "licensing", "production"
    },
    UserRole.ACCOUNTANT: {
        "dashboard", "chart_of_accounts", "journal_entries", "account_ledger",
        "trial_balance", "profit_loss", "balance_sheet", "ar_ageing", "ap_ageing",
        "payments", "expenses", "customers", "suppliers", "returns", "sales_invoice", "purchase_invoice",
        "products", "categories", "warehouses", "batches",
        "budgeting", "tax", "cost_centers", "cashflow", "settings", "intelligence_hub"
    },
    UserRole.HR: {
        "dashboard", "employees", "attendance", "leave", "payroll",
        "customers", "suppliers", "settings",
    },
    UserRole.WAREHOUSE: {
        "dashboard", "products", "categories", "warehouses", "batches",
        "sales_invoice", "purchase_invoice", "customers", "suppliers", "returns",
    },
    UserRole.CASHIER: {
        "dashboard", "sales_invoice", "customers", "products", "batches", "returns"
    },
    UserRole.PHARMACIST: {
        "dashboard", "sales_invoice", "customers", "products", "batches", "returns",
        "categories", "warehouses"
    },
    UserRole.GENERAL: {
        "dashboard", "customers", "suppliers", "products", "settings",
    },
    UserRole.SUPERVISOR: {
        "dashboard", "products", "categories", "warehouses", "batches",
        "sales_invoice", "purchase_invoice", "customers", "suppliers", "returns",
        "chart_of_accounts", "journal_entries", "account_ledger",
        "trial_balance", "profit_loss", "balance_sheet", "ar_ageing", "ap_ageing",
        "payments", "expenses", "employees", "attendance", "leave", "payroll",
        "budgeting", "tax", "cost_centers", "cashflow",
        "fixed_assets", "settings", "intelligence_hub"
    }
}


def get_role_from_user_data(user_data: dict) -> UserRole:
    """Determine user role from user data returned by login API."""
    role_str = user_data.get("role", "").lower().strip()
    if role_str:
        try:
            return UserRole(role_str)
        except ValueError:
            pass
    
    # Fallback to permissions-based detection
    permissions = set(user_data.get("permissions", []))
    if any("admin" in p for p in permissions):
        return UserRole.ADMIN
    elif any("finance" in p or "accounting" in p for p in permissions):
        return UserRole.ACCOUNTANT
    elif any("hr" in p or "employee" in p for p in permissions):
        return UserRole.HR
    elif any("inventory" in p or "stock" in p for p in permissions):
        return UserRole.WAREHOUSE
    else:
        return UserRole.GENERAL


def get_visible_navigation_items(role: UserRole) -> Set[str]:
    """Get set of visible navigation item IDs for a given role."""
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[UserRole.GENERAL])


def is_navigation_item_visible(role: UserRole, page_id: str) -> bool:
    """Check if a navigation item is visible for a given role."""
    visible_items = get_visible_navigation_items(role)
    return page_id in visible_items


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_authorization_resolver(user_data: dict) -> AuthorizationResolver:
    """Create an authorization resolver from user data."""
    return AuthorizationResolver(user_data)


def validate_permissions_for_save(permissions: Set[str]) -> Tuple[bool, List[str]]:
    """Validate permissions before saving (UI hint only)."""
    return validate_permission_dependencies(permissions)
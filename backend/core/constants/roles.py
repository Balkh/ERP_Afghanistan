"""
User role constants for the ERP system.

CANONICAL ROLE REGISTRY — This is the single source of truth for all role names.
Backend seeding (seed_roles.py), ui_scopes.py, and frontend (role_manager.py) MUST
use these names to maintain cross-layer contract alignment.

See also:
    - backend/security/ui_scopes.py       (module-level scope mapping)
    - backend/security/management/commands/seed_roles.py (DB seeding)
    - frontend/ui/role_manager.py          (frontend enum + nav mapping)
"""


class UserRole:
    """System user roles — canonical names for cross-layer contract."""
    ADMIN = 'Admin'
    MANAGER = 'Manager'
    SUPERVISOR = 'Supervisor'
    ACCOUNTANT = 'Accountant'
    PHARMACIST = 'Pharmacist'
    CASHIER = 'Cashier'
    WAREHOUSE = 'Warehouse'
    HR = 'HR'
    GENERAL = 'General'

    CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Manager'),
        (SUPERVISOR, 'Supervisor'),
        (ACCOUNTANT, 'Accountant'),
        (PHARMACIST, 'Pharmacist'),
        (CASHIER, 'Cashier'),
        (WAREHOUSE, 'Warehouse'),
        (HR, 'HR Staff'),
        (GENERAL, 'General User'),
    ]

    # Domain-level permission hints (used by ui_scopes.py for scope resolution)
    PERMISSIONS = {
        ADMIN: ['*'],
        MANAGER: ['sales', 'purchases', 'inventory', 'accounting', 'reports', 'hr', 'finance'],
        SUPERVISOR: ['sales', 'purchases', 'inventory', 'accounting', 'reports', 'hr', 'finance', 'system'],
        ACCOUNTANT: ['accounting', 'reports', 'sales', 'purchases', 'finance'],
        PHARMACIST: ['sales', 'inventory'],
        CASHIER: ['sales'],
        WAREHOUSE: ['inventory'],
        HR: ['hr', 'reports'],
        GENERAL: ['reports'],
    }

    @classmethod
    def all_names(cls) -> list:
        """Return all canonical role names."""
        return [v for k, v in vars(cls).items() if not k.startswith('_') and k != 'CHOICES' and k != 'PERMISSIONS' and k != 'all_names']


class Permission:
    """Permission action constants."""
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'

    ALL = [CREATE, READ, UPDATE, DELETE]
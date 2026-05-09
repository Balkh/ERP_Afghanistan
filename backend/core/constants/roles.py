"""
User role constants for the ERP system.
"""

class UserRole:
    """System user roles."""
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    ACCOUNTANT = 'ACCOUNTANT'
    PHARMACIST = 'PHARMACIST'
    SALES = 'SALES'
    PURCHASE = 'PURCHASE'
    WAREHOUSE = 'WAREHOUSE'
    VIEW_ONLY = 'VIEW_ONLY'
    
    CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Manager'),
        (ACCOUNTANT, 'Accountant'),
        (PHARMACIST, 'Pharmacist'),
        (SALES, 'Sales Staff'),
        (PURCHASE, 'Purchase Staff'),
        (WAREHOUSE, 'Warehouse Staff'),
        (VIEW_ONLY, 'View Only'),
    ]
    
    PERMISSIONS = {
        ADMIN: ['*'],
        MANAGER: ['sales', 'purchases', 'inventory', 'accounting', 'reports'],
        ACCOUNTANT: ['accounting', 'reports', 'sales', 'purchases'],
        PHARMACIST: ['sales', 'inventory'],
        SALES: ['sales'],
        PURCHASE: ['purchases'],
        WAREHOUSE: ['inventory'],
        VIEW_ONLY: ['reports'],
    }


class Permission:
    """Permission constants."""
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    
    ALL = [CREATE, READ, UPDATE, DELETE]
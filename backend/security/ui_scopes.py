"""UI Scope Resolution Module.

Maps user roles to UI scopes for frontend navigation and feature access control.
This module is part of the security layer and must stay in sync with role definitions.
"""
from core.constants.roles import UserRole


def resolve_ui_scopes(roles: list) -> dict:
    """Resolve UI scopes from user roles.
    
    Args:
        roles: List of role names (strings)
    
    Returns:
        Dict mapping domain areas to permission sets
    """
    if not roles:
        return {}
    
    # Aggregate permissions from all roles
    aggregated_permissions = set()
    for role_name in roles:
        perms = UserRole.PERMISSIONS.get(role_name, [])
        if '*' in perms:
            # Admin has all permissions
            return {'*': ['read', 'write', 'delete', 'admin']}
        aggregated_permissions.update(perms)
    
    # Build scope mapping
    scopes = {}
    for domain in aggregated_permissions:
        scopes[domain] = ['read', 'write']
    
    # Add specific module scopes based on domains
    if 'sales' in aggregated_permissions:
        scopes['sales_invoices'] = ['read', 'write']
        scopes['sales_returns'] = ['read', 'write']
        scopes['customers'] = ['read', 'write']
    
    if 'purchases' in aggregated_permissions:
        scopes['purchase_invoices'] = ['read', 'write']
        scopes['purchase_returns'] = ['read', 'write']
        scopes['suppliers'] = ['read', 'write']
    
    if 'inventory' in aggregated_permissions:
        scopes['products'] = ['read', 'write']
        scopes['stock'] = ['read', 'write']
        scopes['warehouses'] = ['read', 'write']
        scopes['stock_movements'] = ['read']
    
    if 'accounting' in aggregated_permissions:
        scopes['journal_entries'] = ['read', 'write']
        scopes['accounts'] = ['read', 'write']
        scopes['financial_reports'] = ['read']
    
    if 'hr' in aggregated_permissions:
        scopes['employees'] = ['read', 'write']
        scopes['payroll'] = ['read', 'write']
        scopes['attendance'] = ['read', 'write']
    
    if 'finance' in aggregated_permissions:
        scopes['payments'] = ['read', 'write']
        scopes['receipts'] = ['read', 'write']
        scopes['banking'] = ['read', 'write']
    
    if 'reports' in aggregated_permissions:
        scopes['reports_all'] = ['read']
    
    if 'system' in aggregated_permissions:
        scopes['system_config'] = ['read', 'write']
        scopes['users'] = ['read', 'write']
        scopes['roles'] = ['read', 'write']
    
    return scopes

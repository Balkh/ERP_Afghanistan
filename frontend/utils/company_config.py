"""
Company Config Loader — Single frontend entry point for company identity.

All frontend code MUST use this utility to access company configuration.
NEVER hardcode company name, currency, or tax info.
NEVER read from local JSON files for business config.

Usage:
    from utils.company_config import get_company_config
    config = await get_company_config(api_client)
    print(config.company_name)
"""
from typing import Optional


class CompanyConfig:
    """Immutable company configuration from backend SSOT."""
    
    __slots__ = ('name', 'code', 'address', 'phone', 'email', 'tax_number',
                 'registration_number', 'default_currency', 'secondary_currency',
                 'invoice_prefix', 'invoice_footer', 'has_logo')
    
    def __init__(self, data: dict):
        self.name = data.get('company_name', 'Pharmacy ERP')
        self.code = data.get('company_code', '')
        self.address = data.get('address', '')
        self.phone = data.get('phone', '')
        self.email = data.get('email', '')
        self.tax_number = data.get('tax_number', '')
        self.registration_number = data.get('registration_number', '')
        self.default_currency = data.get('default_currency', 'AFN')
        self.secondary_currency = data.get('secondary_currency', 'USD')
        self.invoice_prefix = data.get('invoice_prefix', 'INV')
        self.invoice_footer = data.get('invoice_footer', '')
        self.has_logo = data.get('has_logo', False)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'tax_number': self.tax_number,
            'default_currency': self.default_currency,
            'invoice_footer': self.invoice_footer,
        }


_cache: Optional[CompanyConfig] = None


async def get_company_config(api_client) -> CompanyConfig:
    """Load company config from backend API (SSOT).
    
    Caches result for the session. Call this once at app startup.
    """
    global _cache
    if _cache is not None:
        return _cache
    
    try:
        resp = api_client.get("/api/companies/config/")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                data = data.get("data", data)
            _cache = CompanyConfig(data)
            return _cache
    except Exception:
        pass
    
    _cache = CompanyConfig({})
    return _cache


def get_cached_config() -> Optional[CompanyConfig]:
    """Get cached config without API call. Returns None if not loaded."""
    return _cache


def clear_cache():
    """Clear cached config (e.g., after company profile update)."""
    global _cache
    _cache = None

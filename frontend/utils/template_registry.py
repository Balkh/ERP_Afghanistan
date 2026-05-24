"""
Document Template Registry — stores and retrieves print templates by document type.
Templates are fetched from the backend InvoiceTemplate model with local fallback.
"""

from typing import Dict, Any, Optional
from api.client import APIClient


class DocumentType:
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE = "purchase"
    LABEL = "label"
    SHELF_LABEL = "shelf_label"
    REPORT = "report"
    PAYMENT = "payment"
    RETURN = "return"
    STOCK_ADJUSTMENT = "stock_adjustment"
    TRANSFER = "transfer"


class TemplateRegistry:
    """
    Central registry for document print templates.
    Fetches active template from backend, falls back to bundled defaults.
    """

    _DEFAULT_TEMPLATES = {
        DocumentType.INVOICE: {
            "name": "Standard Invoice",
            "layout": "detailed",
            "show_qr": True,
            "field_visibility": {
                "batch": True, "discount": True, "tax": True,
                "notes": True, "phone": True, "address": True
            },
        },
        DocumentType.RECEIPT: {
            "name": "Compact Receipt",
            "layout": "compact",
            "show_qr": True,
            "width_px": 280,
        },
        DocumentType.LABEL: {
            "name": "Barcode Label",
            "width_mm": 50,
            "height_mm": 30,
            "show_price": True,
            "show_barcode": True,
        },
        DocumentType.SHELF_LABEL: {
            "name": "Shelf Label",
            "width_mm": 100,
            "height_mm": 60,
            "show_price": True,
            "show_barcode": True,
            "font_size_large": True,
        },
    }

    def __init__(self, api_client: Optional[APIClient] = None):
        self._api_client = api_client
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_template(self, doc_type: str) -> Dict[str, Any]:
        if doc_type in self._cache:
            return self._cache[doc_type]

        template = self._fetch_from_backend(doc_type)
        if not template:
            template = self._DEFAULT_TEMPLATES.get(doc_type, {}).copy()
        self._cache[doc_type] = template
        return template

    def _fetch_from_backend(self, doc_type: str) -> Optional[Dict[str, Any]]:
        if not self._api_client:
            return None
        try:
            response = self._api_client.get("/api/core/invoice-templates/active/")
            if response and isinstance(response, dict):
                config = response.get("config", {})
                if config.get("layout_type"):
                    return config
        except Exception:
            pass
        return None

    def refresh(self):
        self._cache.clear()

    def register_template(self, doc_type: str, config: Dict[str, Any]):
        self._cache[doc_type] = config

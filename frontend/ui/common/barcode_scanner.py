"""
Backward-compatibility shim — all logic now lives in barcode_search.py.
Import from ui.common.barcode_search instead.
"""

from ui.common.barcode_search import (  # noqa: F401
    BarcodeSearchLineEdit as BarcodeScannerInput,
    SearchResultsDropdown as BarcodeSearchResultsDropdown,
)

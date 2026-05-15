"""
Label Printing System — generates and prints barcode labels, shelf labels, and batch labels.
Supports PDF sheets, thermal labels, and individual label preview.
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class LabelSize(Enum):
    BARCODE_50x30 = (50, 30)
    SHELF_100x60 = (100, 60)
    BATCH_70x40 = (70, 40)
    PRICE_40x25 = (40, 25)


class LabelContent:
    """Represents a single label's content."""

    def __init__(self, product_name: str = "", barcode: str = "",
                 price: str = "", batch: str = "", expiry: str = "",
                 additional: Optional[Dict[str, str]] = None):
        self.product_name = product_name
        self.barcode = barcode
        self.price = price
        self.batch = batch
        self.expiry = expiry
        self.additional = additional or {}


class LabelGenerator:
    """Generates labels in HTML (for PDF/print) and ESC/POS (for thermal)."""

    @staticmethod
    def generate_html(label: LabelContent, size: LabelSize = LabelSize.BARCODE_50x30) -> str:
        w_mm, h_mm = size.value
        return f"""<html><body style="width:{w_mm}mm;height:{h_mm}mm;margin:2mm;font-family:Arial;">
<div style="font-size:9pt;font-weight:bold;text-align:center;">{label.product_name}</div>
<div style="font-size:8pt;text-align:center;">{label.price}</div>
{('<div style="font-size:7pt;text-align:center;">Batch: ' + label.batch + '</div>') if label.batch else ''}
{('<div style="font-size:7pt;text-align:center;">Exp: ' + label.expiry + '</div>') if label.expiry else ''}
<div style="font-size:6pt;text-align:center;margin-top:2mm;">{label.barcode}</div>
</body></html>"""

    @staticmethod
    def generate_sheet_html(labels: List[LabelContent], cols: int = 3,
                            size: LabelSize = LabelSize.BARCODE_50x30) -> str:
        rows_html = ""
        for i, label in enumerate(labels):
            label_html = LabelGenerator.generate_html(label, size)
            if (i + 1) % cols == 0:
                rows_html += f'<tr><td>{label_html}</td></tr>'
            else:
                rows_html += f'<tr><td>{label_html}</td></tr>'
        return f"<html><body><table>{rows_html}</table></body></html>"

    @staticmethod
    def generate_batch_labels(products: List[Dict[str, Any]]) -> List[LabelContent]:
        labels = []
        for p in products:
            name = p.get("name", p.get("generic_name", "Unknown"))
            price = f"{p.get('sale_price', 0):.2f} AFN"
            barcode = p.get("barcode", p.get("sku", ""))
            label = LabelContent(
                product_name=name[:30],
                barcode=barcode[:20],
                price=price,
            )
            batches = p.get("batches", [])
            if batches:
                batch = batches[0]
                label.batch = batch.get("batch_number", "")[:15]
                label.expiry = batch.get("expiry_date", "")[:10]
            labels.append(label)
        return labels


class LabelPrinter:
    """High-level API for printing labels to various targets."""

    def __init__(self, api_client=None):
        self._api_client = api_client

    def print_product_label(self, product: Dict[str, Any], size: LabelSize = LabelSize.BARCODE_50x30):
        labels = LabelGenerator.generate_batch_labels([product])
        from utils.print_engine import PrintEngine
        engine = PrintEngine(self._api_client)
        for lbl in labels:
            html = LabelGenerator.generate_html(lbl, size)
            engine._print_html(html, f"Label - {lbl.product_name}")

    def print_batch_labels(self, products: List[Dict[str, Any]],
                           size: LabelSize = LabelSize.BARCODE_50x30):
        labels = LabelGenerator.generate_batch_labels(products)
        from utils.print_engine import PrintEngine
        engine = PrintEngine(self._api_client)
        sheet_html = LabelGenerator.generate_sheet_html(labels, cols=3, size=size)
        engine._print_html(sheet_html, "Batch Labels")

    def print_thermal_label(self, label: LabelContent, width_mm: int = 50):
        try:
            from utils.thermal_printer import ThermalPrinter, PrinterWidth
            pw = PrinterWidth.MM_80 if width_mm >= 80 else PrinterWidth.MM_58
            tp = ThermalPrinter(pw)
            tp.init().align_center()
            tp.set_size(2, 2).text_line(label.product_name[:20]).set_size(1, 1)
            if label.price:
                tp.text_line(label.price)
            if label.batch:
                tp.text_line(f"Batch: {label.batch}")
            if label.expiry:
                tp.text_line(f"Exp: {label.expiry}")
            if label.barcode:
                tp.newline().barcode_code128(label.barcode)
            tp.newline(2).cut()
            tp.print_raw()
            return True
        except Exception:
            return False

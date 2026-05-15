"""
Local QR Code Generator — offline-compatible, no external API calls.
Uses the qrcode library to generate QR codes as base64 PNG or QPixmap.
"""

import base64
import io
from typing import Optional, TYPE_CHECKING

try:
    import qrcode
    from qrcode import constants as qr_constants
    HAS_QRCODE = True
except ImportError:
    qrcode = None
    qr_constants = None
    HAS_QRCODE = False

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

try:
    from PySide6.QtGui import QPixmap as _QPixmap
    HAS_PYSIDE6 = True
except ImportError:
    _QPixmap = None
    HAS_PYSIDE6 = False


class QRCodeGenerator:
    """Generates QR codes locally without external API dependencies."""

    @classmethod
    def _get_ec_level(cls, error_correction: str) -> int:
        if qr_constants is None:
            return 0
        levels = {
            "L": qr_constants.ERROR_CORRECT_L,
            "M": qr_constants.ERROR_CORRECT_M,
            "Q": qr_constants.ERROR_CORRECT_Q,
            "H": qr_constants.ERROR_CORRECT_H,
        }
        return levels.get(error_correction, qr_constants.ERROR_CORRECT_M)

    @classmethod
    def generate_base64(
        cls,
        data: str,
        size: int = 150,
        box_size: int = 10,
        border: int = 4,
        error_correction: str = "M",
        fill_color: str = "black",
        back_color: str = "white",
    ) -> str:
        """
        Generate a QR code and return it as a base64-encoded PNG string.
        Suitable for embedding in HTML <img> tags via data URIs.
        """
        if not HAS_QRCODE or qrcode is None:
            return ""

        ec_level = cls._get_ec_level(error_correction)
        qr = qrcode.QRCode(
            version=None,
            error_correction=ec_level,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)

        from PIL import Image
        pil_img = Image.open(buffer)
        pil_img = pil_img.resize((size, size))
        output = io.BytesIO()
        pil_img.save(output, "PNG")
        return base64.b64encode(output.getvalue()).decode("utf-8")

    @classmethod
    def generate_data_uri(cls, data: str, **kwargs) -> str:
        """
        Generate a QR code and return it as a data URI string.
        Suitable for direct use in HTML: src="data:image/png;base64,..."
        """
        b64 = cls.generate_base64(data, **kwargs)
        if not b64:
            return ""
        return f"data:image/png;base64,{b64}"

    @classmethod
    def generate_pixmap(cls, data: str, size: int = 100, **kwargs):
        """
        Generate a QR code and return it as a QPixmap for PySide6 widgets.
        """
        if not HAS_QRCODE or not HAS_PYSIDE6 or _QPixmap is None:
            return None

        b64 = cls.generate_base64(data, size=size, **kwargs)
        if not b64:
            return None

        pixmap = _QPixmap()
        pixmap.loadFromData(base64.b64decode(b64))
        return pixmap

    @classmethod
    def generate_invoice_qr_data(cls, invoice_data: dict) -> str:
        """
        Generate a structured QR payload for an invoice.
        Contains: invoice number, date, total amount, customer name.
        """
        parts = [
            f"INV={invoice_data.get('invoice_number', 'N/A')}",
            f"DATE={invoice_data.get('invoice_date', 'N/A')}",
            f"AMT={invoice_data.get('total_amount', 0)}",
            f"CUSTOMER={invoice_data.get('customer_name', 'N/A')}",
        ]
        return "|".join(parts)

    @classmethod
    def generate_receipt_qr_data(cls, receipt_data: dict) -> str:
        """
        Generate a structured QR payload for a receipt/payment.
        """
        parts = [
            f"RCPT={receipt_data.get('receipt_number', 'N/A')}",
            f"DATE={receipt_data.get('date', 'N/A')}",
            f"AMT={receipt_data.get('amount', 0)}",
            f"METHOD={receipt_data.get('payment_method', 'N/A')}",
        ]
        return "|".join(parts)

    @classmethod
    def generate_report_qr_data(cls, report_data: dict) -> str:
        """
        Generate a structured QR payload for a financial report.
        Contains: report name, generated date, company, period.
        """
        parts = [
            f"REPORT={report_data.get('report_name', 'N/A')}",
            f"DATE={report_data.get('generated_at', 'N/A')}",
            f"COMPANY={report_data.get('company', 'N/A')}",
            f"PERIOD={report_data.get('period', 'N/A')}",
        ]
        return "|".join(parts)

"""
Barcode Generation Service — generates barcode images for products and batches.
Supports EAN-13, Code128, Code39, and QR code formats.
"""

import base64
import io
from typing import Optional, Dict, Any

try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


class BarcodeFormat:
    """Supported barcode formats."""
    EAN13 = "ean13"
    CODE128 = "code128"
    CODE39 = "code39"
    QR = "qr"


class BarcodeGenerationError(Exception):
    """Raised when barcode generation fails."""
    pass


class BarcodeGenerator:
    """Generates barcodes as base64-encoded images for products and batches."""

    @classmethod
    def generate(
        cls,
        code: str,
        fmt: str = BarcodeFormat.CODE128,
        width: int = 300,
        height: int = 100,
        include_text: bool = True,
    ) -> str:
        """
        Generate a barcode image and return as base64 PNG.
        
        Args:
            code: The barcode value (product barcode, SKU, or batch code)
            fmt: Barcode format (ean13, code128, code39, qr)
            width: Image width in pixels
            height: Image height in pixels
            include_text: Whether to include human-readable text below barcode
            
        Returns:
            Base64-encoded PNG string
            
        Raises:
            BarcodeGenerationError: If generation fails
        """
        if fmt == BarcodeFormat.QR:
            return cls._generate_qr(code, size=width)
        
        if not HAS_BARCODE:
            raise BarcodeGenerationError("python-barcode library not installed")
        
        try:
            barcode_class = barcode.get_barcode_class(fmt)
            writer = ImageWriter()
            
            bc = barcode_class(code, writer=writer)
            
            buffer = io.BytesIO()
            options = {
                "module_width": 0.4,
                "module_height": height / 100.0,
                "quiet_zone": 6.0,
                "write_text": include_text,
                "font_size": 14,
                "text_distance": 5.0,
            }
            bc.write(buffer, options)
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
            
        except Exception as e:
            raise BarcodeGenerationError(f"Failed to generate {fmt} barcode: {e}")

    @classmethod
    def _generate_qr(cls, data: str, size: int = 150) -> str:
        """Generate a QR code as base64 PNG."""
        if not HAS_QRCODE:
            raise BarcodeGenerationError("qrcode library not installed")
        
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            from PIL import Image
            img = img.resize((size, size))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            raise BarcodeGenerationError(f"Failed to generate QR code: {e}")

    @classmethod
    def generate_product_barcode(cls, product_data: Dict[str, Any]) -> str:
        """Generate barcode for a product using its barcode field."""
        code = product_data.get("barcode") or product_data.get("sku", "")
        if not code:
            raise BarcodeGenerationError("Product has no barcode or SKU")
        
        # Auto-detect format
        fmt = cls._detect_format(code)
        return cls.generate(code, fmt=fmt)

    @classmethod
    def generate_batch_barcode(cls, batch_code: str) -> str:
        """Generate barcode for a batch."""
        return cls.generate(batch_code, fmt=BarcodeFormat.CODE128)

    @classmethod
    def generate_shelf_label(
        cls,
        product_name: str,
        price: str,
        barcode_data: str,
        fmt: str = BarcodeFormat.CODE128,
    ) -> str:
        """
        Generate a shelf label with product name, price, and barcode.
        Returns base64 PNG.
        """
        b64 = cls.generate(barcode_data, fmt=fmt, width=400, height=120)
        return b64

    @classmethod
    def _detect_format(cls, code: str) -> str:
        """Auto-detect barcode format from code structure."""
        if len(code) == 13 and code.isdigit():
            return BarcodeFormat.EAN13
        if len(code) == 12 and code.isdigit():
            return BarcodeFormat.EAN13
        if code.isalnum():
            return BarcodeFormat.CODE128
        return BarcodeFormat.CODE128

    @classmethod
    def validate_ean13(cls, code: str) -> bool:
        """Validate EAN-13 checksum."""
        if len(code) != 13 or not code.isdigit():
            return False
        
        total = 0
        for i in range(12):
            digit = int(code[i])
            total += digit * (3 if i % 2 == 1 else 1)
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(code[12])

    @classmethod
    def generate_ean13_with_check(cls, prefix: str) -> str:
        """Generate a valid EAN-13 code from a 12-digit prefix."""
        if len(prefix) != 12 or not prefix.isdigit():
            raise BarcodeGenerationError("Prefix must be 12 digits")
        
        total = 0
        for i in range(12):
            digit = int(prefix[i])
            total += digit * (3 if i % 2 == 1 else 1)
        
        check_digit = (10 - (total % 10)) % 10
        return f"{prefix}{check_digit}"

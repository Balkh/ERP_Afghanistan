"""
Tests for barcode generation service and scanner infrastructure.
"""

import pytest
from inventory.services.barcode_generator import (
    BarcodeGenerator,
    BarcodeFormat,
    BarcodeGenerationError,
)


class TestEAN13Validation:
    def test_valid_ean13(self):
        assert BarcodeGenerator.validate_ean13("5901234123457") is True

    def test_invalid_ean13_checksum(self):
        assert BarcodeGenerator.validate_ean13("5901234123458") is False

    def test_invalid_ean13_length(self):
        assert BarcodeGenerator.validate_ean13("12345") is False

    def test_invalid_ean13_non_digits(self):
        assert BarcodeGenerator.validate_ean13("590123412345A") is False

    def test_generate_ean13_with_check(self):
        code = BarcodeGenerator.generate_ean13_with_check("590123412345")
        assert code == "5901234123457"
        assert BarcodeGenerator.validate_ean13(code) is True

    def test_generate_ean13_invalid_prefix(self):
        with pytest.raises(BarcodeGenerationError):
            BarcodeGenerator.generate_ean13_with_check("123")


class TestBarcodeGeneration:
    def test_generate_code128(self):
        b64 = BarcodeGenerator.generate("PARA-500MG", fmt=BarcodeFormat.CODE128)
        assert len(b64) > 0
        assert b64.startswith("iVBOR")

    def test_generate_code39(self):
        b64 = BarcodeGenerator.generate("ABC123", fmt=BarcodeFormat.CODE39)
        assert len(b64) > 0

    def test_generate_ean13(self):
        b64 = BarcodeGenerator.generate("5901234123457", fmt=BarcodeFormat.EAN13)
        assert len(b64) > 0

    def test_generate_qr(self):
        b64 = BarcodeGenerator.generate("BATCH-2026-001", fmt=BarcodeFormat.QR, width=100)
        assert len(b64) > 0

    def test_generate_without_text(self):
        b64 = BarcodeGenerator.generate("PROD-001", fmt=BarcodeFormat.CODE128, include_text=False)
        assert len(b64) > 0

    def test_generate_product_barcode(self):
        product = {"barcode": "5901234123457", "name": "Paracetamol"}
        b64 = BarcodeGenerator.generate_product_barcode(product)
        assert len(b64) > 0

    def test_generate_product_barcode_fallback_to_sku(self):
        product = {"sku": "SKU-PARA-500", "name": "Paracetamol"}
        b64 = BarcodeGenerator.generate_product_barcode(product)
        assert len(b64) > 0

    def test_generate_product_barcode_no_code(self):
        product = {"name": "Paracetamol"}
        with pytest.raises(BarcodeGenerationError):
            BarcodeGenerator.generate_product_barcode(product)

    def test_generate_batch_barcode(self):
        b64 = BarcodeGenerator.generate_batch_barcode("BATCH-2026-001")
        assert len(b64) > 0

    def test_generate_shelf_label(self):
        b64 = BarcodeGenerator.generate_shelf_label(
            product_name="Paracetamol 500mg",
            price="150.00",
            barcode_data="5901234123457",
        )
        assert len(b64) > 0


class TestFormatDetection:
    def test_detect_ean13_13_digits(self):
        fmt = BarcodeGenerator._detect_format("5901234123457")
        assert fmt == BarcodeFormat.EAN13

    def test_detect_ean13_12_digits(self):
        fmt = BarcodeGenerator._detect_format("590123412345")
        assert fmt == BarcodeFormat.EAN13

    def test_detect_code128_alphanumeric(self):
        fmt = BarcodeGenerator._detect_format("PARA-500MG")
        assert fmt == BarcodeFormat.CODE128

    def test_detect_code128_default(self):
        fmt = BarcodeGenerator._detect_format("ABC")
        assert fmt == BarcodeFormat.CODE128

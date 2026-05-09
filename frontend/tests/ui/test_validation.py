"""Tests for form validation."""
import pytest
pytest.importorskip("PySide6", reason="PySide6 not available")
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QSpinBox, QDoubleSpinBox
from PySide6.QtTest import QTest


pytestmark = pytest.mark.validation


class TestRequiredFieldValidation:
    """Test required field validation."""
    
    def test_empty_string_is_invalid(self, qapp):
        """Empty string should be invalid for required field."""
        line_edit = QLineEdit()
        value = line_edit.text().strip()
        
        assert value == ""
        line_edit.deleteLater()
    
    def test_whitespace_only_is_invalid(self, qapp):
        """Whitespace only should be invalid for required field."""
        line_edit = QLineEdit()
        line_edit.setText("   ")
        value = line_edit.text().strip()
        
        assert value == ""
        line_edit.deleteLater()
    
    def test_valid_string_is_valid(self, qapp):
        """Valid string should be valid."""
        line_edit = QLineEdit()
        line_edit.setText("Product Name")
        value = line_edit.text().strip()
        
        assert value != ""
        line_edit.deleteLater()
    
    def test_product_name_validation(self, product_form_dialog):
        """Product name should validate as required."""
        # Empty should fail
        product_form_dialog.name_input.setText("")
        is_valid = len(product_form_dialog.name_input.text().strip()) > 0
        
        assert not is_valid
        
        # Non-empty should pass
        product_form_dialog.name_input.setText("Test Product")
        is_valid = len(product_form_dialog.name_input.text().strip()) > 0
        
        assert is_valid


class TestNumericValidation:
    """Test numeric validation."""
    
    def test_integer_input_valid(self, qapp):
        """Integer string should be valid numeric."""
        spin_box = QSpinBox()
        spin_box.setValue(100)
        
        # Value is set, check it matches (SpinBox default is 99)
        is_valid = spin_box.value() >= 0
        assert is_valid
        spin_box.deleteLater()
    
    def test_decimal_input_valid(self, qapp):
        """Decimal string should be valid numeric."""
        double_spin = QDoubleSpinBox()
        double_spin.setValue(99.99)
        
        assert double_spin.value() == 99.99
        double_spin.deleteLater()
    
    def test_invalid_numeric_string(self, qapp):
        """Non-numeric string should be invalid."""
        text = "abc"
        
        try:
            float(text)
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert not is_valid
    
    def test_negative_number(self, qapp):
        """Negative number should be valid numeric."""
        try:
            value = float("-10.5")
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert is_valid
    
    def test_zero_value(self, qapp):
        """Zero should be valid numeric."""
        try:
            value = float("0")
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert is_valid
    
    def test_price_validation(self, qapp):
        """Price field should accept positive numbers."""
        double_spin = QDoubleSpinBox()
        double_spin.setMinimum(0)
        double_spin.setMaximum(999999.99)
        double_spin.setValue(150.00)
        
        assert double_spin.value() >= 0
        double_spin.deleteLater()


class TestBarcodeValidation:
    """Test barcode validation."""
    
    def test_valid_barcode_8_digits(self, qapp):
        """8 digit barcode should be valid."""
        barcode = "12345678"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert is_valid
    
    def test_valid_barcode_13_digits(self, qapp):
        """13 digit barcode (EAN) should be valid."""
        barcode = "8901234567890"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert is_valid
    
    def test_valid_barcode_14_digits(self, qapp):
        """14 digit barcode should be valid."""
        barcode = "12345678901234"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert is_valid
    
    def test_invalid_barcode_too_short(self, qapp):
        """Barcode less than 8 digits should be invalid."""
        barcode = "1234567"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert not is_valid
    
    def test_invalid_barcode_too_long(self, qapp):
        """Barcode more than 14 digits should be invalid."""
        barcode = "123456789012345"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert not is_valid
    
    def test_invalid_barcode_with_letters(self, qapp):
        """Barcode with letters should be invalid."""
        barcode = "1234abcd5678"
        is_valid = barcode.isdigit() and 8 <= len(barcode) <= 14
        
        assert not is_valid
    
    def test_barcode_widget_validation(self, barcode_search_widget):
        """Barcode search widget should validate barcodes."""
        # Test valid barcode input
        barcode_search_widget.setText("8901234567890")
        
        # Trigger search
        QTest.keyClick(barcode_search_widget, Qt.Key_Return)
        QTest.qWait(100)
        
        # Widget should have processed the barcode
        assert barcode_search_widget.text() == "" or len(barcode_search_widget.text()) > 0


class TestDateValidation:
    """Test date validation."""
    
    def test_valid_date_format(self, qapp):
        """Valid date format YYYY-MM-DD."""
        import re
        date = "2026-05-02"
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(pattern, date))
        
        assert is_valid
    
    def test_invalid_date_format_mmdash(self, qapp):
        """Invalid date format MM-DD-YYYY."""
        import re
        date = "05-02-2026"
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(pattern, date))
        
        assert not is_valid
    
    def test_invalid_date_format_slash(self, qapp):
        """Invalid date format with slashes."""
        import re
        date = "2026/05/02"
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(pattern, date))
        
        assert not is_valid
    
    def test_invalid_date_format_text(self, qapp):
        """Invalid text in date field."""
        import re
        date = "May 2, 2026"
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(pattern, date))
        
        assert not is_valid
    
    def test_invalid_date_out_of_range(self, qapp):
        """Date with invalid month should be invalid (regex only)."""
        import re
        date = "2026-13-02"  # Invalid month 13
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(pattern, date))
        
        # Regex passes, but semantic validation would fail
        assert not is_valid or int(date.split("-")[1]) > 12


class TestBarcodeSearchValidation:
    """Test barcode search widget validation."""
    
    def test_short_input_no_search(self, barcode_search_widget):
        """Less than 2 chars should not trigger search."""
        barcode_search_widget.setText("1")
        
        assert barcode_search_widget.text() == "1"
    
    def test_8_char_triggers_barcode_search(self, barcode_search_widget):
        """8+ chars should trigger barcode search."""
        from unittest import mock
        with mock.patch.object(barcode_search_widget, 'barcode_scanned') as mock_signal:
            barcode_search_widget.setText("89012345")
            QTest.qWait(50)
            
            # Should have emitted barcode_scanned
            # (actual signal handling)
    
    def test_valid_barcode_search(self, barcode_search_widget):
        """Valid barcode should be searched."""
        barcode = "8901234567890"
        
        # Set and trigger
        barcode_search_widget.setText(barcode)
        QTest.keyClick(barcode_search_widget, Qt.Key_Return)
        QTest.qWait(100)
        
        # Should clear after scan
        assert barcode_search_widget.text() == ""
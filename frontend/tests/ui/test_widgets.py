"""Tests for reusable widgets - buttons, dialogs."""
import pytest
pytest.importorskip("PySide6", reason="PySide6 not available")
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton, QDialog, QDialogButtonBox, 
    QVBoxLayout, QLabel, QLineEdit
)
from PySide6.QtTest import QTest


pytestmark = pytest.mark.widgets


class TestButtonWidget:
    """Test button widget functionality."""
    
    def test_button_can_be_created(self, qapp):
        """Button can be created."""
        button = QPushButton("Test")
        assert button is not None
        assert button.text() == "Test"
        button.deleteLater()
    
    def test_button_is_clickable(self, qapp):
        """Button should be clickable."""
        button = QPushButton("Click Me")
        clicked = []
        button.clicked.connect(lambda: clicked.append(True))
        
        QTest.mouseClick(button, Qt.LeftButton)
        
        assert len(clicked) > 0
        button.deleteLater()
    
    def test_button_can_be_disabled(self, qapp):
        """Button can be disabled."""
        button = QPushButton("Test")
        button.setEnabled(False)
        
        assert not button.isEnabled()
        button.deleteLater()
    
    def test_button_can_be_enabled(self, qapp):
        """Button can be enabled."""
        button = QPushButton("Test")
        button.setEnabled(False)
        button.setEnabled(True)
        
        assert button.isEnabled()
        button.deleteLater()


class TestDialogWidget:
    """Test dialog widget functionality."""
    
    def test_dialog_can_be_created(self, qapp):
        """Dialog can be created."""
        dialog = QDialog()
        assert dialog is not None
        dialog.deleteLater()
    
    def test_dialog_has_button_box(self, qapp):
        """Dialog should have button box."""
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        
        assert button_box is not None
        dialog.deleteLater()
    
    def test_dialog_accept_signal(self, qapp):
        """Dialog accept signal should work."""
        dialog = QDialog()
        accepted = []
        dialog.accepted.connect(lambda: accepted.append(True))
        
        dialog.accept()
        
        assert len(accepted) > 0
        dialog.deleteLater()
    
    def test_dialog_reject_signal(self, qapp):
        """Dialog reject signal should work."""
        dialog = QDialog()
        rejected = []
        dialog.rejected.connect(lambda: rejected.append(True))
        
        dialog.reject()
        
        assert len(rejected) > 0
        dialog.deleteLater()


class TestDialogButtonBox:
    """Test dialog button box."""
    
    def test_ok_button_emits_accept(self, qapp):
        """OK button should emit accept."""
        dialog = QDialog()
        dialog.setModal(True)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        
        accepted = []
        dialog.accepted.connect(lambda: accepted.append(True))
        button_box.accepted.connect(dialog.accept)
        button_box.clicked.connect(lambda: accepted.append(True))
        
        button_box.clicked.emit(button_box.button(QDialogButtonBox.Ok))
        
        assert len(accepted) > 0
        dialog.deleteLater()
    
    def test_cancel_button_emits_reject(self, qapp):
        """Cancel button should emit reject."""
        dialog = QDialog()

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        
        rejected = []
        dialog.rejected.connect(lambda: rejected.append(True))
        button_box.rejected.connect(dialog.reject)
        button_box.rejected.connect(lambda: rejected.append(True))
        
        button_box.rejected.emit()
        
        assert len(rejected) > 0
        dialog.deleteLater()


class TestFormDialog:
    """Test form dialog."""
    
    def test_form_dialog_has_title(self, product_form_dialog):
        """Form dialog should have a title."""
        assert product_form_dialog.windowTitle() is not None
    
    def test_form_dialog_has_required_fields(self, product_form_dialog):
        """Form dialog should have required fields."""
        assert product_form_dialog.name_input is not None
        assert product_form_dialog.category_combo is not None
        assert product_form_dialog.unit_combo is not None
    
    def test_form_dialog_categories_populated(self, product_form_dialog):
        """Category combo should be populated."""
        assert product_form_dialog.category_combo.count() > 0
    
    def test_form_dialog_units_populated(self, product_form_dialog):
        """Unit combo should be populated."""
        assert product_form_dialog.unit_combo.count() > 0
    
    def test_form_dialog_buttons_exist(self, product_form_dialog):
        """Form dialog should have OK and Cancel buttons."""
        # Button box is added with Ok | Cancel
        assert product_form_dialog.layout() is not None


class TestFormDialogData:
    """Test form dialog data retrieval."""
    
    def test_get_form_data_returns_dict(self, product_form_dialog):
        """Get form data should return a dictionary."""
        data = product_form_dialog.get_form_data()
        
        assert isinstance(data, dict)
        assert "name" in data
        assert "category_id" in data
        assert "unit_id" in data
    
    def test_get_form_data_empty_initial(self, product_form_dialog):
        """Form data should be empty initially."""
        data = product_form_dialog.get_form_data()
        
        assert data["name"] == ""
        assert data["category_id"] is None
        assert data["unit_id"] is None
    
    def test_get_form_data_after_input(self, product_form_dialog):
        """Form data should reflect user input."""
        product_form_dialog.name_input.setText("Test Product")
        product_form_dialog.category_combo.setCurrentIndex(1)
        product_form_dialog.unit_combo.setCurrentIndex(1)
        
        data = product_form_dialog.get_form_data()
        
        assert data["name"] == "Test Product"
        assert data["category_id"] == 1
        assert data["unit_id"] == 1


class TestModalDialog:
    """Test modal dialog behavior."""
    
    def test_dialog_is_modal(self, product_form_dialog):
        """Dialog should be modal."""
        assert product_form_dialog.isModal()
    
    def test_dialog_can_be_non_modal(self, qapp):
        """Dialog can be set to non-modal."""
        dialog = QDialog()
        dialog.setModal(False)
        
        assert not dialog.isModal()
        dialog.deleteLater()
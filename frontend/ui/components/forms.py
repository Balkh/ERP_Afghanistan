from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
"""
Enterprise Form Components.
Professional form widgets with validation.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QRadioButton, QDateEdit, QTimeEdit, QDateTimeEdit,
    QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt, QDate, QTime, QDateTime
from PySide6.QtGui import QValidator
from typing import Any, Optional, Callable, Dict, List
from enum import Enum
import re


class FieldType(Enum):
    """Form field types."""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DECIMAL = "decimal"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    RADIO = "radio"


class ValidationRule:
    """Validation rule definition."""
    
    def __init__(self, rule_type: str, message: str, params: Dict = None):
        self.rule_type = rule_type
        self.message = message
        self.params = params or {}
        
    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate value. Returns (is_valid, error_message)."""
        if self.rule_type == "required":
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, self.message
                
        elif self.rule_type == "min_length":
            if value and len(str(value)) < self.params.get("min", 0):
                return False, self.message
                
        elif self.rule_type == "max_length":
            if value and len(str(value)) > self.params.get("max", 100):
                return False, self.message
                
        elif self.rule_type == "min":
            try:
                if value is not None and float(value) < self.params.get("min", 0):
                    return False, self.message
            except (ValueError, TypeError):
                pass
                
        elif self.rule_type == "max":
            try:
                if value is not None and float(value) > self.params.get("max", 0):
                    return False, self.message
            except (ValueError, TypeError):
                pass
                
        elif self.rule_type == "email":
            if value and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(value)):
                return False, self.message
                
        elif self.rule_type == "phone":
            if value and not re.match(r'^[\d\+\-\s]{7,}$', str(value)):
                return False, self.message
                
        elif self.rule_type == "pattern":
            pattern = self.params.get("pattern", "")
            if value and not re.match(pattern, str(value)):
                return False, self.message
                
        return True, ""


class FormField(QWidget):
    """
    Form field widget with label, input, and validation.
    """
    
    value_changed = Signal(object)
    validation_changed = Signal(bool, str)
    
    def __init__(
        self,
        field_type: FieldType,
        label: str = "",
        name: str = "",
        validators: List[ValidationRule] = None,
        placeholder: str = "",
        default_value: Any = None,
        required: bool = False,
        readonly: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._field_type = field_type
        self._label = label
        self._name = name
        self._validators = validators or []
        self._placeholder = placeholder
        self._default_value = default_value
        self._required = required
        self._readonly = readonly
        self._value = default_value
        self._error_message = ""
        self._input_widget = None
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup field UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_XS)
        
        # Create label
        self._label_widget = QLabel(self._label)
        if self._required:
            self._label_widget.setText(f"{self._label} *")
        layout.addWidget(self._label_widget)
        
        # Create input based on type
        self._input_widget = self._create_input()
        
        if self._input_widget:
            layout.addWidget(self._input_widget)
            
        # Create error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 10px;")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)
        
        # Set placeholder
        if self._placeholder and hasattr(self._input_widget, 'setPlaceholderText'):
            self._input_widget.setPlaceholderText(self._placeholder)
            
    def _create_input(self) -> QWidget:
        """Create input widget based on field type."""
        
        if self._field_type == FieldType.TEXT:
            widget = QLineEdit()
            widget.setMaxLength(255)
            
        elif self._field_type == FieldType.TEXTAREA:
            widget = QTextEdit()
            widget.setMaximumHeight(100)
            
        elif self._field_type == FieldType.NUMBER:
            widget = QSpinBox()
            widget.setRange(-999999999, 999999999)
            
        elif self._field_type == FieldType.DECIMAL:
            widget = QDoubleSpinBox()
            widget.setRange(-999999999.99, 999999999.99)
            widget.setDecimals(2)
            
        elif self._field_type == FieldType.EMAIL:
            widget = QLineEdit()
            widget.setMaxLength(255)
            
        elif self._field_type == FieldType.PHONE:
            widget = QLineEdit()
            widget.setMaxLength(20)
            
        elif self._field_type == FieldType.DATE:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            
        elif self._field_type == FieldType.TIME:
            widget = QTimeEdit()
            widget.setTime(QTime.currentTime())
            
        elif self._field_type == FieldType.DATETIME:
            widget = QDateTimeEdit()
            widget.setDateTime(QDateTime.currentDateTime())
            
        elif self._field_type == FieldType.SELECT:
            widget = QComboBox()
            widget.setEditable(False)
            
        elif self._field_type == FieldType.CHECKBOX:
            widget = QCheckBox()
            
        else:
            widget = QLineEdit()
            
        if self._readonly:
            widget.setEnabled(False)
            
        return widget
        
    def _connect_signals(self):
        """Connect input signals."""
        if isinstance(self._input_widget, QLineEdit):
            self._input_widget.textChanged.connect(self._on_value_changed)
        elif isinstance(self._input_widget, (QSpinBox, QDoubleSpinBox)):
            self._input_widget.valueChanged.connect(self._on_value_changed)
        elif isinstance(self._input_widget, QComboBox):
            self._input_widget.currentIndexChanged.connect(self._on_value_changed)
        elif isinstance(self._input_widget, QCheckBox):
            self._input_widget.stateChanged.connect(self._on_value_changed)
        elif isinstance(self._input_widget, (QDateEdit, QTimeEdit, QDateTimeEdit)):
            self._input_widget.dateTimeChanged.connect(self._on_value_changed)
        elif isinstance(self._input_widget, QTextEdit):
            self._input_widget.textChanged.connect(self._on_value_changed)
            
    def _on_value_changed(self, value: Any = None):
        """Handle value change."""
        self.set_value(self.get_value())
        
    def set_value(self, value: Any):
        """Set field value."""
        old_value = self._value
        self._value = value
        
        # Update input widget
        if self._input_widget:
            if isinstance(self._input_widget, QLineEdit):
                self._input_widget.setText(str(value) if value else "")
            elif isinstance(self._input_widget, QSpinBox):
                self._input_widget.setValue(int(value) if value else 0)
            elif isinstance(self._input_widget, QDoubleSpinBox):
                self._input_widget.setValue(float(value) if value else 0.0)
            elif isinstance(self._input_widget, QComboBox):
                # Find index by value
                for i in range(self._input_widget.count()):
                    if self._input_widget.itemData(i) == value:
                        self._input_widget.setCurrentIndex(i)
                        break
            elif isinstance(self._input_widget, QCheckBox):
                self._input_widget.setChecked(bool(value))
                
        if old_value != value:
            self.value_changed.emit(value)
            
        # Validate
        self.validate()
        
    def get_value(self) -> Any:
        """Get field value."""
        if not self._input_widget:
            return self._value
            
        if isinstance(self._input_widget, QLineEdit):
            return self._input_widget.text()
        elif isinstance(self._input_widget, QTextEdit):
            return self._input_widget.toPlainText()
        elif isinstance(self._input_widget, (QSpinBox, QDoubleSpinBox)):
            return self._input_widget.value()
        elif isinstance(self._input_widget, QComboBox):
            return self._input_widget.currentData()
        elif isinstance(self._input_widget, QCheckBox):
            return self._input_widget.isChecked()
        elif isinstance(self._input_widget, QDateEdit):
            return self._input_widget.date().toString("yyyy-MM-dd")
        elif isinstance(self._input_widget, QTimeEdit):
            return self._input_widget.time().toString("HH:mm:ss")
        elif isinstance(self._input_widget, QDateTimeEdit):
            return self._input_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            
        return self._value
        
    def validate(self) -> bool:
        """Validate field value."""
        # Check required
        if self._required:
            value = self.get_value()
            if value is None or (isinstance(value, str) and not value.strip()):
                self.set_error("This field is required")
                return False
                
        # Run validators
        for validator in self._validators:
            is_valid, message = validator.validate(self.get_value())
            if not is_valid:
                self.set_error(message)
                return False
                
        self.clear_error()
        return True
        
    def set_error(self, message: str):
        """Set error message."""
        self._error_message = message
        self._error_label.setText(message)
        self._error_label.setVisible(bool(message))
        
        # Add error style to input
        if self._input_widget:
            self._input_widget.setStyleSheet(f"border: 1px solid {COLOR_DANGER};")
            
        self.validation_changed.emit(False, message)
        
    def clear_error(self):
        """Clear error message."""
        self._error_message = ""
        self._error_label.setVisible(False)
        
        if self._input_widget:
            self._input_widget.setStyleSheet("")
            
        self.validation_changed.emit(True, "")
        
    def set_options(self, options: List[tuple]):
        """Set options for select fields."""
        if isinstance(self._input_widget, QComboBox):
            self._input_widget.clear()
            for label, value in options:
                self._input_widget.addItem(label, value)
                
    def is_valid(self) -> bool:
        """Check if field is valid."""
        return self._error_message == ""


class EnterpriseForm(QWidget):
    """
    Enterprise form with multiple fields.
    """
    
    form_submitted = Signal(dict)
    form_validated = Signal(dict)
    form_changed = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._fields: Dict[str, FormField] = {}
        self._field_order: List[str] = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Form layout
        self._form_layout = QFormLayout()
        self._form_layout.setSpacing(SPACING_MD)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(self._form_layout)
        
    def add_field(
        self,
        name: str,
        field_type: FieldType,
        label: str,
        **kwargs
    ) -> FormField:
        """Add field to form."""
        field = FormField(
            field_type=field_type,
            label=label,
            name=name,
            required=kwargs.get('required', False),
            placeholder=kwargs.get('placeholder', ''),
            default_value=kwargs.get('default'),
            validators=kwargs.get('validators', [])
        )
        
        self._fields[name] = field
        self._field_order.append(name)
        
        self._form_layout.addRow(label + (" *" if kwargs.get('required') else ""), field)
        
        field.value_changed.connect(lambda v: self._on_field_changed(name, v))
        
        return field
        
    def _on_field_changed(self, name: str, value: Any):
        """Handle field change."""
        data = self.get_data()
        self.form_changed.emit(data)
        
    def get_field(self, name: str) -> Optional[FormField]:
        """Get field by name."""
        return self._fields.get(name)
        
    def get_data(self) -> Dict[str, Any]:
        """Get form data."""
        return {name: field.get_value() for name, field in self._fields.items()}
        
    def set_data(self, data: Dict[str, Any]):
        """Set form data."""
        for name, value in data.items():
            if name in self._fields:
                self._fields[name].set_value(value)
                
    def validate(self) -> tuple[bool, Dict[str, str]]:
        """Validate all fields."""
        errors = {}
        is_valid = True
        
        for name, field in self._fields.items():
            if not field.validate():
                errors[name] = field._error_message
                is_valid = False
                
        return is_valid, errors
        
    def submit(self) -> bool:
        """Submit form."""
        is_valid, errors = self.validate()
        
        if is_valid:
            data = self.get_data()
            self.form_validated.emit(data)
            self.form_submitted.emit(data)
            return True
            
        return False
        
    def reset(self):
        """Reset form."""
        for field in self._fields.values():
            field.set_value(field._default_value)
            field.clear_error()
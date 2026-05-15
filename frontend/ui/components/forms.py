from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE, MARGIN_CARD, COLOR_DANGER, TEXT_ERROR,
                           TEXT_CARD_TITLE, TEXT_LABEL,
                           COLOR_TEXT_PRIMARY, COLOR_BORDER, BORDER_RADIUS_MD,
                           INPUT_HEIGHT_MD)
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
        self._error_label.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_ERROR}px;")
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
    
    Usage:
        form = EnterpriseForm()
        form.add_field("name", FieldType.TEXT, "Name", required=True)
        form.add_field("email", FieldType.EMAIL, "Email")
        form.add_action_buttons(save_text="Save", cancel_text="Cancel")
        form.form_submitted.connect(self.on_submit)
    """
    
    form_submitted = Signal(dict)
    form_validated = Signal(dict)
    form_changed = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._fields: Dict[str, FormField] = {}
        self._field_order: List[str] = []
        self._input_widgets: List[QWidget] = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Form layout
        self._form_layout = QFormLayout()
        self._form_layout.setSpacing(SPACING_MD)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        self._scroll_content = QWidget()
        self._scroll_content.setLayout(self._form_layout)
        
        from PySide6.QtWidgets import QScrollArea
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setWidget(self._scroll_content)
        
        layout.addWidget(self._scroll_area)
        
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
        
        # Apply standardized input height
        if field._input_widget and hasattr(field._input_widget, 'setMinimumHeight'):
            from ui.constants import INPUT_HEIGHT_MD
            field._input_widget.setMinimumHeight(INPUT_HEIGHT_MD)
        
        self._fields[name] = field
        self._field_order.append(name)
        
        self._form_layout.addRow(field._label_widget, field)
        
        # Track input widgets for tab order
        if field._input_widget:
            self._input_widgets.append(field._input_widget)
        
        field.value_changed.connect(lambda v: self._on_field_changed(name, v))
        
        # Update tab order
        self._update_tab_order()
        
        return field
    
    def _update_tab_order(self):
        """Set tab order to match field insertion order."""
        widgets = [w for w in self._input_widgets if w.isEnabled()]
        for i in range(len(widgets) - 1):
            self.setTabOrder(widgets[i], widgets[i + 1])
        
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
        """Validate all fields. Scrolls to first error."""
        errors = {}
        is_valid = True
        first_error_field = None
        
        for name, field in self._fields.items():
            if not field.validate():
                errors[name] = field._error_message
                is_valid = False
                if first_error_field is None:
                    first_error_field = field
        
        # Scroll to first error
        if first_error_field is not None and hasattr(self, '_scroll_area'):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._scroll_area.ensureWidgetVisible(first_error_field))
            if first_error_field._input_widget:
                first_error_field._input_widget.setFocus()
                
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
    
    def add_action_buttons(self, save_text: str = "Save", cancel_text: str = "Cancel",
                           save_callback=None, cancel_callback=None):
        """Add standardized action button bar to form."""
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QFrame, QSizePolicy
        from ui.constants import BUTTON_HEIGHT_MD, SPACING_SM
        from ui.constants import COLOR_BORDER, SPACING_MD
        
        button_bar = QFrame()
        button_bar.setFrameShape(QFrame.NoFrame)
        bar_layout = QHBoxLayout(button_bar)
        bar_layout.setContentsMargins(0, SPACING_MD, 0, 0)
        bar_layout.setSpacing(SPACING_SM)
        
        bar_layout.addStretch()
        
        if cancel_text:
            cancel_btn = QPushButton(cancel_text)
            cancel_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
            cancel_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if cancel_callback:
                cancel_btn.clicked.connect(cancel_callback)
            else:
                cancel_btn.clicked.connect(lambda: self.window().close() if self.window() else None)
            bar_layout.addWidget(cancel_btn)
        
        if save_text:
            save_btn = QPushButton(save_text)
            save_btn.setMinimumHeight(BUTTON_HEIGHT_MD)
            save_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            from ui.constants import COLOR_PRIMARY, COLOR_TEXT_ON_PRIMARY, BORDER_RADIUS_MD
            save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    color: {COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {BORDER_RADIUS_MD}px;
                    font-weight: 600;
                    padding: {SPACING_SM}px {SPACING_XL}px;
                }}
            """)
            if save_callback:
                save_btn.clicked.connect(save_callback)
            else:
                save_btn.clicked.connect(self.submit)
            bar_layout.addWidget(save_btn)
        
        # Add button bar to the main layout after the scroll area
        from PySide6.QtWidgets import QVBoxLayout
        parent_layout = self.layout()
        if isinstance(parent_layout, QVBoxLayout):
            parent_layout.addWidget(button_bar)
        
        return button_bar
        
    def reset(self):
        """Reset form."""
        for field in self._fields.values():
            field.set_value(field._default_value)
            field.clear_error()


class FormSection(QGroupBox):
    """
    Lightweight structural grouping for ERP forms.

    Wraps QGroupBox + QFormLayout for consistent spacing and label alignment.
    Can be placed in any layout (QSplitter, QVBoxLayout, QHBoxLayout, etc.).
    Does NOT enforce scroll containers, validation, or tab order.

    Usage:
        section = FormSection("Customer Information")
        section.add_field(self.customer_combo, "Customer*")
        section.add_field(self.phone_input, "Phone")
        parent_layout.addWidget(section)
    """

    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self._form = QFormLayout(self)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form.setHorizontalSpacing(SPACING_LG)
        self._form.setVerticalSpacing(SPACING_MD)
        self._form.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_MD)
        self.setStyleSheet(f"""
            QGroupBox {{
                font-size: {TEXT_CARD_TITLE}pt;
                font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
        """)

    def add_field(self, widget: QWidget, label: str = "") -> QWidget:
        """Add a field row. Auto-applies INPUT_HEIGHT_MD to input widgets."""
        if hasattr(widget, 'setMinimumHeight'):
            current = widget.minimumHeight()
            if current < INPUT_HEIGHT_MD:
                widget.setMinimumHeight(INPUT_HEIGHT_MD)
        self._form.addRow(label, widget)
        return widget

    def add_row(self, label: str, widget: QWidget) -> QWidget:
        """Alias for add_field."""
        return self.add_field(widget, label)

    def layout(self) -> QFormLayout:
        return self._form
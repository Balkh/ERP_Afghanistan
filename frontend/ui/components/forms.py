from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, COLOR_FORM_LABEL_REQUIRED, INPUT_HEIGHT_MD)
"""
Enterprise Form Components.
Professional form widgets with validation.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QFormLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QDateEdit, QTimeEdit, QDateTimeEdit, QGroupBox, QFrame
)
from PySide6.QtCore import Signal, Qt, QDate, QTime, QDateTime, QTimer
from typing import Any, Optional, Dict, List
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
    Form field widget with label, input, contextual helper text, and inline validation.
    
    Phase 15.9: Enhanced with:
    - Contextual helper text below input (muted, scannable)
    - Inline validation states: success, warning, error
    - Required field visual indicator
    - Validation messages near the field (not modals)
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
        helper_text: str = "",
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
        self._helper_text = helper_text
        self._validation_state = ""  # "", "success", "warning", "error"
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup field UI with helper text and validation support."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)  # Increased spacing for better readability
        
        # Create label
        from theme.style_builder import UIStyleBuilder
        self._label_widget = QLabel(self._label)
        self._label_widget.setStyleSheet(UIStyleBuilder.get_label_style("label"))
        if self._required:
            self._label_widget.setText(f"{self._label} <span style='color: {COLOR_FORM_LABEL_REQUIRED};'>*</span>")
        layout.addWidget(self._label_widget)
        
        # Create input based on type
        self._input_widget = self._create_input()
        
        if self._input_widget:
            # Centralized StyleBuilder abstraction
            from theme.style_builder import UIStyleBuilder
            self._input_widget.setStyleSheet(UIStyleBuilder.get_input_style())
            layout.addWidget(self._input_widget)
            
        # Contextual helper text (muted, always visible)
        if self._helper_text:
            self._helper_label = QLabel(self._helper_text)
            self._helper_label.setStyleSheet(UIStyleBuilder.get_label_style("muted") + " margin-top: 2px;")
            self._helper_label.setWordWrap(True)
            layout.addWidget(self._helper_label)
        else:
            self._helper_label = None
            
        # Validation message label (shown only on error/warning)
        self._validation_label = QLabel()
        self._validation_label.setStyleSheet(UIStyleBuilder.get_label_style("error"))
        self._validation_label.setVisible(False)
        self._validation_label.setWordWrap(True)
        layout.addWidget(self._validation_label)
        
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
        """Set error message with inline validation styling."""
        from theme.style_builder import UIStyleBuilder
        self._error_message = message
        self._validation_state = "error"
        if hasattr(self, '_validation_label'):
            self._validation_label.setText(message)
            self._validation_label.setVisible(True)
            self._validation_label.setStyleSheet(UIStyleBuilder.get_label_style("error"))
        
        # Add error style to input
        if self._input_widget:
            self._input_widget.setStyleSheet(UIStyleBuilder.get_input_style("error"))
            
        self.validation_changed.emit(False, message)
        
    def clear_error(self):
        """Clear error message and reset input styling."""
        from theme.style_builder import UIStyleBuilder
        self._error_message = ""
        self._validation_state = ""
        if hasattr(self, '_validation_label'):
            self._validation_label.setVisible(False)
        
        if self._input_widget:
            self._input_widget.setStyleSheet(UIStyleBuilder.get_input_style("default"))
            
        self.validation_changed.emit(True, "")
        
    def set_success(self, message: str = ""):
        """Set success validation state."""
        from theme.style_builder import UIStyleBuilder
        self._validation_state = "success"
        if hasattr(self, '_validation_label') and message:
            self._validation_label.setText(message)
            self._validation_label.setVisible(True)
            self._validation_label.setStyleSheet(UIStyleBuilder.get_label_style("success"))
        else:
            if hasattr(self, '_validation_label'):
                self._validation_label.setVisible(False)
        if self._input_widget:
            self._input_widget.setStyleSheet(UIStyleBuilder.get_input_style("success"))
        
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
    
    Phase D.1: Enhanced with dirty state, double-submit prevention, auto-save draft.
    
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
    
    DIRTY_STATE_CHANGED = Signal(bool)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._fields: Dict[str, FormField] = {}
        self._field_order: List[str] = []
        self._input_widgets: List[QWidget] = []
        self._saved_data: Dict[str, Any] = {}
        self._dirty: bool = False
        self._submission_lock: bool = False
        self._draft_key: str = ""
        self._draft_timer: Optional[QTimer] = None
        self._version: int = 0
        
        self._setup_ui()
        self._install_keyboard_shortcuts()
        
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
        
    def _install_keyboard_shortcuts(self):
        """Install keyboard shortcuts (Ctrl+S to save, Escape to cancel)."""
        from PySide6.QtGui import QShortcut, QKeySequence
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.submit)

    # ── Dirty State ──

    def is_dirty(self) -> bool:
        """Check if form has unsaved changes."""
        return self._dirty

    def mark_dirty(self):
        """Mark form as having unsaved changes."""
        if not self._dirty:
            self._dirty = True
            self.DIRTY_STATE_CHANGED.emit(True)

    def mark_clean(self):
        """Mark form as clean (no unsaved changes)."""
        self._saved_data = self.get_data()
        if self._dirty:
            self._dirty = False
            self.DIRTY_STATE_CHANGED.emit(False)

    def reset_dirty_state(self):
        """Reset dirty state without marking clean (for partial resets)."""
        self._dirty = False
        self.DIRTY_STATE_CHANGED.emit(False)

    # ── Draft Save / Restore ──

    def enable_draft_autosave(self, draft_key: str, interval_ms: int = 5000):
        """Enable periodic draft auto-save."""
        self._draft_key = draft_key
        if self._draft_timer:
            self._draft_timer.stop()
        self._draft_timer = QTimer(self)
        self._draft_timer.timeout.connect(self._auto_save_draft)
        self._draft_timer.start(interval_ms)

    def disable_draft_autosave(self):
        """Disable draft auto-save."""
        if self._draft_timer:
            self._draft_timer.stop()
            self._draft_timer = None
        self._draft_key = ""

    def _auto_save_draft(self):
        """Auto-save draft if form is dirty."""
        if self._dirty and self._draft_key:
            self.save_draft()

    def save_draft(self, draft_key: str = "") -> bool:
        """Save form data as draft. Returns True if saved."""
        key = draft_key or self._draft_key
        if not key:
            return False
        try:
            import os
            from utils.atomic_io import atomic_write_json
            draft_dir = os.path.join(os.path.expanduser("~"), ".pharmacy_erp", "drafts")
            draft_path = os.path.join(draft_dir, f"{key}.json")
            atomic_write_json(draft_path, self.get_data())
            return True
        except Exception:
            return False

    def restore_draft(self, draft_key: str = "") -> bool:
        """Restore form data from draft. Returns True if restored."""
        key = draft_key or self._draft_key
        if not key:
            return False
        try:
            import json, os
            draft_path = os.path.join(os.path.expanduser("~"), ".pharmacy_erp", "drafts", f"{key}.json")
            if os.path.exists(draft_path):
                with open(draft_path) as f:
                    data = json.load(f)
                self.set_data(data)
                return True
        except Exception:
            pass
        return False

    def clear_draft(self, draft_key: str = ""):
        """Delete saved draft."""
        key = draft_key or self._draft_key
        if not key:
            return
        try:
            import os
            draft_path = os.path.join(os.path.expanduser("~"), ".pharmacy_erp", "drafts", f"{key}.json")
            if os.path.exists(draft_path):
                os.remove(draft_path)
        except Exception:
            pass

    # ── Optimistic Locking ──

    @property
    def version(self) -> int:
        """Get form version counter for optimistic locking."""
        return self._version

    def set_version(self, version: int):
        """Set version counter for optimistic locking."""
        self._version = version

    def increment_version(self):
        """Increment version counter."""
        self._version += 1

    def has_stale_data(self, server_version: int) -> bool:
        """Check if form data is stale compared to server version."""
        return server_version > self._version

    # ── Field Management ──

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
        """Handle field change with dirty state detection."""
        data = self.get_data()
        if data != self._saved_data:
            self.mark_dirty()
        else:
            self.reset_dirty_state()
        self.form_changed.emit(data)
        
    def get_field(self, name: str) -> Optional[FormField]:
        """Get field by name."""
        return self._fields.get(name)
        
    def get_data(self) -> Dict[str, Any]:
        """Get form data."""
        return {name: field.get_value() for name, field in self._fields.items()}
        
    def set_data(self, data: Dict[str, Any], mark_clean: bool = True):
        """Set form data with optional clean state snapshot."""
        for name, value in data.items():
            if name in self._fields:
                self._fields[name].set_value(value)
        if mark_clean:
            self.mark_clean()
        self._saved_data = self.get_data()
                
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
        """Submit form with double-submit prevention."""
        if self._submission_lock:
            import logging
            logging.getLogger(__name__).warning("Double submit prevented")
            return False
        
        self._submission_lock = True
        try:
            is_valid, errors = self.validate()
            
            if is_valid:
                data = self.get_data()
                self.form_validated.emit(data)
                self.form_submitted.emit(data)
                self.increment_version()
                self.mark_clean()
                self.clear_draft()
                return True
                
            return False
        finally:
            self._submission_lock = False
    
    def add_action_buttons(self, save_text: str = "Save", cancel_text: str = "Cancel",
                           save_callback=None, cancel_callback=None):
        """Add standardized action button bar to form."""
        from PySide6.QtWidgets import QHBoxLayout, QFrame
        from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
        
        button_bar = QFrame()
        button_bar.setFrameShape(QFrame.NoFrame)
        bar_layout = QHBoxLayout(button_bar)
        bar_layout.setContentsMargins(0, SPACING_MD, 0, 0)
        bar_layout.setSpacing(SPACING_SM)
        
        bar_layout.addStretch()
        
        if cancel_text:
            cancel_btn = EnterpriseButton(cancel_text, variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
            if cancel_callback:
                cancel_btn.clicked.connect(cancel_callback)
            else:
                cancel_btn.clicked.connect(lambda: self.window().close() if self.window() else None)
            bar_layout.addWidget(cancel_btn)
        
        if save_text:
            save_btn = EnterpriseButton(save_text, variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
            if save_callback:
                save_btn.clicked.connect(save_callback)
            else:
                save_btn.clicked.connect(self.submit)
            bar_layout.addWidget(save_btn)
        
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
    v3 — Enterprise form section with progressive visual hierarchy.

    Single-column mode (default): uses QFormLayout, labels beside inputs.
    2-column grid mode: uses QGridLayout, labels ABOVE inputs (muted style).

    Features:
    - Subtle section divider below title
    - Increased vertical rhythm between sections
    - Surface elevation distinction
    - Primary fields visually emphasized, secondary/optional fields softer

    Usage:
        # Single column
        section = FormSection("Details", primary=True)
        section.add_field(widget, "Label")

        # 2-column grid
        section = FormSection("Identity", columns=2, primary=True)
        section.add_field_pair("Name*:", name_widget, "Generic Name:", generic_widget)
        section.add_full_width("Description:", text_widget)
    """

    def __init__(self, title: str = "", columns: int = 1, primary: bool = True, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self._columns = columns
        self._grid_row = 0
        self._primary = primary

        margin_top = SPACING_LG if primary else SPACING_MD
        if columns == 2:
            self._grid = QGridLayout(self)
            self._grid.setHorizontalSpacing(SPACING_XL)
            self._grid.setVerticalSpacing(SPACING_MD)
            self._grid.setContentsMargins(SPACING_MD, margin_top, SPACING_MD, SPACING_MD)
        else:
            self._form = QFormLayout(self)
            self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            self._form.setHorizontalSpacing(SPACING_LG)
            self._form.setVerticalSpacing(SPACING_MD)
            self._form.setContentsMargins(SPACING_MD, margin_top, SPACING_MD, SPACING_MD)

        from theme.style_builder import UIStyleBuilder
        self.setStyleSheet(UIStyleBuilder.get_form_section_style(primary))

    def set_primary(self, primary: bool):
        """Set whether this section is primary (emphasized) or secondary (softer)."""
        self._primary = primary

    def _make_label(self, text: str, required: bool = False) -> QLabel:
        """Create a muted label above an input."""
        from theme.style_builder import UIStyleBuilder
        lbl = QLabel(text)
        if required:
            lbl.setText(f"{text} *")
        lbl.setStyleSheet(UIStyleBuilder.get_label_style("label_small"))
        return lbl

    def _apply_input_height(self, widget: QWidget) -> None:
        if hasattr(widget, 'setMinimumHeight'):
            current = widget.minimumHeight()
            if current < INPUT_HEIGHT_MD:
                widget.setMinimumHeight(INPUT_HEIGHT_MD)

    def add_field(self, widget: QWidget, label: str = "") -> QWidget:
        """Add a single field row (single-column mode)."""
        self._apply_input_height(widget)
        self._form.addRow(label, widget)
        return widget

    def add_row(self, label: str, widget: QWidget) -> QWidget:
        """Alias for add_field."""
        return self.add_field(widget, label)

    def _make_helper_label(self, text: str) -> QLabel:
        """Create a contextual helper text label (muted, tiny)."""
        from theme.style_builder import UIStyleBuilder
        lbl = QLabel(text)
        lbl.setStyleSheet(UIStyleBuilder.get_label_style("helper"))
        lbl.setWordWrap(True)
        return lbl

    def add_field_pair(self, label1: str, widget1: QWidget, label2: str, widget2: QWidget,
                       required1: bool = False, required2: bool = False,
                       helper1: str = "", helper2: str = "") -> None:
        """Add a 2-column row with labels above inputs and optional helper text."""
        self._apply_input_height(widget1)
        self._apply_input_height(widget2)

        cell1 = QVBoxLayout()
        cell1.setContentsMargins(0, 0, 0, 0)
        cell1.setSpacing(SPACING_XS)
        cell1.addWidget(self._make_label(label1, required=required1))
        cell1.addWidget(widget1)
        if helper1:
            cell1.addWidget(self._make_helper_label(helper1))

        cell2 = QVBoxLayout()
        cell2.setContentsMargins(0, 0, 0, 0)
        cell2.setSpacing(SPACING_XS)
        cell2.addWidget(self._make_label(label2, required=required2))
        cell2.addWidget(widget2)
        if helper2:
            cell2.addWidget(self._make_helper_label(helper2))

        cell1_w = QWidget()
        cell1_w.setLayout(cell1)
        cell2_w = QWidget()
        cell2_w.setLayout(cell2)

        self._grid.addWidget(cell1_w, self._grid_row, 0)
        self._grid.addWidget(cell2_w, self._grid_row, 1)
        self._grid_row += 1

    def add_full_width(self, label: str, widget: QWidget, required: bool = False,
                       helper: str = "") -> None:
        """Add a full-width field spanning both columns with optional helper text."""
        self._apply_input_height(widget)

        cell = QVBoxLayout()
        cell.setContentsMargins(0, 0, 0, 0)
        cell.setSpacing(SPACING_XS)
        cell.addWidget(self._make_label(label, required=required))
        cell.addWidget(widget)
        if helper:
            cell.addWidget(self._make_helper_label(helper))

        cell_w = QWidget()
        cell_w.setLayout(cell)

        self._grid.addWidget(cell_w, self._grid_row, 0, 1, 2)
        self._grid_row += 1

    def add_separator(self):
        """Add a subtle visual separator between field groups within a section."""
        from theme.style_builder import UIStyleBuilder
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(UIStyleBuilder.get_divider_style())
        if self._columns == 2:
            self._grid.addWidget(line, self._grid_row, 0, 1, 2)
            self._grid_row += 1
        else:
            self._form.addRow(line)

    def layout(self):
        return self._grid if self._columns == 2 else self._form
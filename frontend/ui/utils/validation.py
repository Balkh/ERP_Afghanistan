"""Validation utilities for ERP forms."""
import re
from PySide6.QtGui import QValidator


class ValidationRules:
    """Common validation rules."""
    
    # Regex patterns
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE_PATTERN = r'^[\+]?[0-9\s\-\(\)]{10,}$'
    AFN_CURRENCY_PATTERN = r'^\d{1,10}(\.\d{0,2})?$'
    USD_CURRENCY_PATTERN = r'^\d{1,10}(\.\d{0,2})?$'
    ALPHA_PATTERN = r'^[a-zA-Z\s\-]+$'
    ALPHANUMERIC_PATTERN = r'^[a-zA-Z0-9\s\-_]+$'
    CODE_PATTERN = r'^[A-Z0-9\-_]+$'
    
    @staticmethod
    def is_valid_email(email):
        """Validate email format."""
        if not email:
            return True  # Optional field
        return bool(re.match(ValidationRules.EMAIL_PATTERN, email))
    
    @staticmethod
    def is_valid_phone(phone):
        """Validate phone number format."""
        if not phone:
            return True  # Optional field
        return bool(re.match(ValidationRules.PHONE_PATTERN, phone.replace(' ', '')))
    
    @staticmethod
    def is_valid_currency(value, currency="AFN"):
        """Validate currency format."""
        try:
            float_val = float(value)
            return float_val >= 0
        except ValueError:
            return False
    
    @staticmethod
    def is_required(value):
        """Check if value is not empty."""
        return bool(str(value).strip())


class FormValidator:
    """Form validation helper."""
    
    def __init__(self):
        self.errors = {}
    
    def validate_required(self, field_name, value, error_message=None):
        """Validate required field."""
        if not ValidationRules.is_required(value):
            self.errors[field_name] = error_message or f"{field_name} is required"
            return False
        return True
    
    def validate_email(self, field_name, value, error_message=None):
        """Validate email field."""
        if value and not ValidationRules.is_valid_email(value):
            self.errors[field_name] = error_message or f"Invalid {field_name} format"
            return False
        return True
    
    def validate_phone(self, field_name, value, error_message=None):
        """Validate phone field."""
        if value and not ValidationRules.is_valid_phone(value):
            self.errors[field_name] = error_message or f"Invalid {field_name} format"
            return False
        return True
    
    def validate_currency(self, field_name, value, currency="AFN", error_message=None):
        """Validate currency field."""
        if value and not ValidationRules.is_valid_currency(value, currency):
            self.errors[field_name] = error_message or f"Invalid {field_name} format"
            return False
        return True
    
    def validate_min_length(self, field_name, value, min_length, error_message=None):
        """Validate minimum length."""
        if value and len(str(value)) < min_length:
            self.errors[field_name] = error_message or f"{field_name} must be at least {min_length} characters"
            return False
        return True
    
    def validate_max_length(self, field_name, value, max_length, error_message=None):
        """Validate maximum length."""
        if value and len(str(value)) > max_length:
            self.errors[field_name] = error_message or f"{field_name} must not exceed {max_length} characters"
            return False
        return True
    
    def validate_pattern(self, field_name, value, pattern, error_message=None):
        """Validate against regex pattern."""
        if value and not re.match(pattern, value):
            self.errors[field_name] = error_message or f"Invalid {field_name} format"
            return False
        return True
    
    def has_errors(self):
        """Check if there are validation errors."""
        return len(self.errors) > 0
    
    def get_errors(self):
        """Get all validation errors."""
        return self.errors.copy()
    
    def clear_errors(self):
        """Clear all validation errors."""
        self.errors.clear()


class InputValidator(QValidator):
    """Input validator for real-time field validation."""
    
    def __init__(self, validation_func, parent=None):
        super().__init__(parent)
        self.validation_func = validation_func
    
    def validate(self, input_text, pos):
        """Validate input text."""
        is_valid = self.validation_func(input_text)
        if is_valid:
            return (QValidator.Acceptable, input_text, pos)
        else:
            return (QValidator.Invalid, input_text, pos)


def create_email_validator(parent=None):
    """Create email validator."""
    return InputValidator(ValidationRules.is_valid_email, parent)


def create_phone_validator(parent=None):
    """Create phone validator."""
    return InputValidator(ValidationRules.is_valid_phone, parent)


def create_currency_validator(currency="AFN", parent=None):
    """Create currency validator."""
    return InputValidator(lambda x: ValidationRules.is_valid_currency(x, currency), parent)


def create_required_validator(parent=None):
    """Create required field validator."""
    return InputValidator(ValidationRules.is_required, parent)
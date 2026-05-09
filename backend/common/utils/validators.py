"""
Common validation utilities.
"""
import re
from django.core.exceptions import ValidationError


def validate_phone_number(value: str) -> None:
    """
    Validate a phone number format.
    
    Args:
        value: Phone number string
        
    Raises:
        ValidationError: If the phone number is invalid
    """
    pattern = re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$')
    if not pattern.match(value):
        raise ValidationError('Invalid phone number format.')


def validate_email(value: str) -> None:
    """
    Validate an email format.
    
    Args:
        value: Email string
        
    Raises:
        ValidationError: If the email is invalid
    """
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not pattern.match(value):
        raise ValidationError('Invalid email format.')


def validate_positive_decimal(value) -> None:
    """
    Validate that a value is a positive decimal.
    
    Args:
        value: Decimal value
        
    Raises:
        ValidationError: If the value is not positive
    """
    if value <= 0:
        raise ValidationError('Value must be positive.')


def validate_non_negative_decimal(value) -> None:
    """
    Validate that a value is a non-negative decimal.
    
    Args:
        value: Decimal value
        
    Raises:
        ValidationError: If the value is negative
    """
    if value < 0:
        raise ValidationError('Value cannot be negative.')
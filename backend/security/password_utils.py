import hashlib
import secrets
import bcrypt
from django.conf import settings
from django.contrib.auth.hashers import (
    make_password as django_make_password,
    check_password as django_check_password,
    is_password_usable as django_is_password_usable
)
from django.core.exceptions import ValidationError
import re


def make_password(raw_password):
    """
    Secure password hashing using bcrypt with configurable rounds
    Falls back to Django's default if bcrypt is not available
    """
    try:
        # Use bcrypt if available for stronger security
        # Generate a salt and hash the password
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(raw_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except ImportError:
        # Fallback to Django's password hasher
        return django_make_password(raw_password)
    except Exception as e:
        # Log the error and fallback to Django
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Bcrypt hashing failed, falling back to Django: {e}")
        return django_make_password(raw_password)


def check_password(raw_password, encoded_password):
    """
    Check a plain-text password against its hashed version
    """
    try:
        # Check if it's a bcrypt hash
        if encoded_password.startswith('$2b$') or encoded_password.startswith('$2a$') or encoded_password.startswith('$2y$'):
            return bcrypt.checkpw(raw_password.encode('utf-8'), encoded_password.encode('utf-8'))
        else:
            # Use Django's checker for other formats
            return django_check_password(raw_password, encoded_password)
    except ImportError:
        # Fallback to Django's password checker
        return django_check_password(raw_password, encoded_password)
    except Exception as e:
        # Log the error and fallback to Django
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Password checking failed, falling back to Django: {e}")
        return django_check_password(raw_password, encoded_password)


def is_password_usable(encoded_password):
    """
    Check if the password is in a usable format
    """
    try:
        return django_is_password_usable(encoded_password)
    except Exception:
        return False


def generate_secure_token(length=32):
    """
    Generate a cryptographically secure random token
    """
    return secrets.token_urlsafe(length)


def generate_reset_token():
    """
    Generate a secure token for password reset
    """
    return secrets.token_urlsafe(32)


def validate_password_strength(password):
    """
    Validate password strength according to security policy
    Returns list of error messages, empty if valid
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_passwords = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'monkey', 'letmein', 'dragon', 'baseball', 'iloveyou',
        'trustno1', 'sunshine', 'master', 'welcome', 'password123'
    ]
    
    if password.lower() in weak_passwords:
        errors.append("Password is too common and easily guessable")
    
    # Check for repeated characters
    if re.search(r'(.)\1{3,}', password):
        errors.append("Password cannot contain more than 3 identical consecutive characters")
    
    # Check for sequential characters
    sequences = [
        'abcdefghijklmnopqrstuvwxyz',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '0123456789'
    ]
    
    for seq in sequences:
        for i in range(len(seq) - 2):
            if seq[i:i+3] in password.lower():
                errors.append("Password cannot contain sequential characters")
                break
        else:
            continue
        break
    
    return errors


def hash_sensitive_data(data, salt=None):
    """
    Hash sensitive data for storage (not for passwords - use make_password for those)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Use PBKDF2 for sensitive data hashing
    import hashlib
    hashed = hashlib.pbkdf2_hmac('sha256', data, salt, 100000)
    return salt.hex() + hashed.hex()


def verify_sensitive_data(data, hashed):
    """
    Verify sensitive data against its hash
    """
    try:
        salt_hex = hashed[:32]
        hash_hex = hashed[32:]
        salt = bytes.fromhex(salt_hex)
        computed_hash = hash_sensitive_data(data, salt)
        return secrets.compare_digest(computed_hash, hashed)
    except Exception:
        return False
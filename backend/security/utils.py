import re
import html
import logging
import os
import json
import base64
from typing import Any, Dict, List, Optional, Union
from django.conf import settings
from django.core.exceptions import ValidationError, SuspiciousOperation
from django.db import connection
from django.utils.encoding import force_str
from django.utils.http import urlencode
import bleach
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Input validation and sanitization utilities
    """
    
    # Common regex patterns
    PATTERNS = {
        'username': r'^[a-zA-Z0-9._-]{3,30}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?[\d\s\-\(\)]{10,20}$',
        'alphanumeric': r'^[a-zA-Z0-9]+$',
        'alpha': r'^[a-zA-Z\s]+$',
        'numeric': r'^\d+$',
        'decimal': r'^\d+\.?\d*$',
        'currency': r'^\d+\.\d{2}$',
        'safe_string': r'^[a-zA-Z0-9\s\-_\.@]+$',  # Basic safe string
        'url': r'^https?:\/\/[^\s/$.?#].[^\s]*$',
    }
    
    @classmethod
    def validate_input(cls, value: Any, pattern_name: str, field_name: str = "Field") -> bool:
        """
        Validate input against a predefined pattern
        """
        if value is None:
            return False
            
        str_value = str(value).strip()
        if not str_value:
            return False
            
        pattern = cls.PATTERNS.get(pattern_name)
        if not pattern:
            raise ValueError(f"Unknown pattern: {pattern_name}")
            
        return bool(re.match(pattern, str_value))
    
    @classmethod
    def sanitize_html(cls, text: str, tags: List[str] = None, attributes: Dict[str, List[str]] = None) -> str:
        """
        Sanitize HTML input to prevent XSS attacks
        """
        if not text:
            return ""
            
        # Default allowed tags for basic formatting
        if tags is None:
            tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        
        # Default allowed attributes
        if attributes is None:
            attributes = {
                '*': ['class'],
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'width', 'height']
            }
            
        return bleach.clean(
            text,
            tags=tags,
            attributes=attributes,
            strip=True
        )
    
    @classmethod
    def sanitize_sql_like(cls, value: str) -> str:
        """
        Sanitize input for SQL LIKE clauses to prevent injection
        """
        if not value:
            return ""
        # Escape SQL wildcards
        return value.replace('%', r'\%').replace('_', r'\_').replace("'", r"''")
    
    @classmethod
    def prevent_sql_injection(cls, value: str) -> str:
        """
        Basic SQL injection prevention (though Django ORM should handle this)
        This is an additional layer of defense
        """
        if not isinstance(value, str):
            return value
            
        # List of SQL keywords that shouldn't appear in user input in certain contexts
        sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 
            'EXEC', 'TRUNCATE', 'MERGE', 'CALL', '--', ';', '/*', '*/'
        ]
        
        upper_value = value.upper()
        for keyword in sql_keywords:
            if keyword in upper_value:
                logger.warning(f"Potential SQL injection attempt detected: {keyword} in input")
                raise SuspiciousOperation(f"Invalid input: contains prohibited SQL keyword {keyword}")
                
        return value
    
    @classmethod
    def validate_file_upload(cls, filename: str, content_type: str, size: int, 
                           allowed_extensions: List[str] = None,
                           allowed_mimetypes: List[str] = None,
                           max_size: int = None) -> List[str]:
        """
        Validate file upload for security
        Returns list of error messages (empty if valid)
        """
        errors = []
        
        # Check file size
        if max_size and size > max_size:
            errors.append(f"File size exceeds maximum allowed size of {max_size} bytes")
            
        # Check file extension
        if allowed_extensions:
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if ext not in [e.lower().lstrip('.') for e in allowed_extensions]:
                errors.append(f"File extension not allowed. Allowed extensions: {', '.join(allowed_extensions)}")
                
        # Check MIME type
        if allowed_mimetypes:
            if content_type not in allowed_mimetypes:
                errors.append(f"MIME type not allowed. Allowed types: {', '.join(allowed_mimetypes)}")
                
        # Check for dangerous extensions regardless
        dangerous_extensions = ['exe', 'sh', 'php', 'php3', 'php4', 'php5', 'phtml', 
                              'jsp', 'asp', 'aspx', 'cfm', 'pl', 'py', 'rb']
        if filename:
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if ext in dangerous_extensions:
                errors.append(f"File type {ext} is not allowed for security reasons")
                
        return errors


class SecureStorage:
    """
    Secure local data storage utilities
    """
    
    @staticmethod
    def encrypt_data(data: Union[str, bytes], key: bytes = None) -> Dict[str, str]:
        """
        Encrypt data using Fernet symmetric encryption
        Returns dict with encrypted data and key info (key should be stored securely separately)
        """
        if key is None:
            # Generate a key - in production, this should come from secure key management
            key = Fernet.generate_key()
        
        f = Fernet(key)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        encrypted_data = f.encrypt(data)
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'key_reference': base64.b64encode(key).decode('utf-8')  # In production, store key separately
        }
    
    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """
        Decrypt data using Fernet symmetric encryption
        """
        try:
            f = Fernet(key)
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = f.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    @staticmethod
    def hash_for_storage(data: str, salt: bytes = None) -> Dict[str, str]:
        """
        Hash data for secure storage (like API keys, tokens that need verification)
        Uses PBKDF2 with SHA256
        """
        if salt is None:
            salt = secrets.token_bytes(32)
            
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        hashed = kdf.derive(data)
        
        return {
            'hashed_data': base64.b64encode(hashed).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8')
        }
    
    @staticmethod
    def verify_hashed_data(data: str, hashed_storage: Dict[str, str]) -> bool:
        """
        Verify data against its stored hash
        """
        try:
            salt = base64.b64decode(hashed_storage['salt'].encode('utf-8'))
            stored_hash = base64.b64decode(hashed_storage['hashed_data'].encode('utf-8'))
            
            if isinstance(data, str):
                data = data.encode('utf-8')
                
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            computed_hash = kdf.derive(data)
            
            return secrets.compare_digest(computed_hash, stored_hash)
        except Exception as e:
            logger.error(f"Hash verification failed: {e}")
            return False


class ConfigurationEncryption:
    """
    Encrypted sensitive configuration storage
    """
    
    @staticmethod
    def get_encryption_key() -> bytes:
        """
        Get encryption key from environment or generate derivation from SECRET_KEY
        In production, this should come from a secure key management service
        """
        # Derive key from Django SECRET_KEY for consistency
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if not secret_key:
            raise ValueError("SECRET_KEY must be set for configuration encryption")
            
        # Use PBKDF2 to derive a fixed-length key from the secret key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'pharmacy_erp_config_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        key = kdf.derive(secret_key.encode('utf-8'))
        return base64.urlsafe_b64encode(key)  # Fernet requires URL-safe base64-encoded key
    
    @classmethod
    def encrypt_config_value(cls, value: str) -> str:
        """
        Encrypt a configuration value for storage
        """
        try:
            key = cls.get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(value.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Configuration encryption failed: {e}")
            raise
    
    @classmethod
    def decrypt_config_value(cls, encrypted_value: str) -> str:
        """
        Decrypt a configuration value
        """
        try:
            key = cls.get_encryption_key()
            f = Fernet(key)
            decoded = base64.b64decode(encrypted_value.encode('utf-8'))
            decrypted = f.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Configuration decryption failed: {e}")
            raise


class SecurityHeaders:
    """
    Security headers middleware utilities
    """
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get recommended security headers for HTTP responses
        """
        return {
            # Prevent clickjacking
            'X-Frame-Options': 'DENY',
            
            # Enable XSS protection in browsers
            'X-XSS-Protection': '1; mode=block',
            
            # Prevent MIME sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Referrer policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Content Security Policy (adjust based on actual needs)
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            
            # Permissions Policy (formerly Feature Policy)
            'Permissions-Policy': (
                'geolocation=(), '
                'microphone=(), '
                'camera=(), '
                'magnetometer=(), '
                'gyroscope=(), '
                'speaker=()'
            ),
            
            # HSTS would be handled by web server (nginx/apache) in production
            # 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        }


class AuditSecurityLogger:
    """
    Security-focused logging that avoids sensitive data leakage
    """
    
    @staticmethod
    def log_security_event(event_type: str, user_id: int = None, 
                          ip_address: str = None, details: Dict[str, Any] = None,
                          level: str = 'WARNING'):
        """
        Log security events without sensitive data
        """
        logger = logging.getLogger('security')
        
        log_data = {
            'event_type': event_type,
            'user_id': user_id if user_id else 'anonymous',
            'ip_address': ip_address or 'unknown',
            'timestamp': None  # Will be added by logger
        }
        
        # Add non-sensitive details
        if details:
            safe_details = {}
            for key, value in details.items():
                # Skip keys that might contain sensitive data
                sensitive_keys = ['password', 'token', 'secret', 'key', 'authorization', 
                                'credit_card', 'ssn', 'api_key', 'access_token']
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    safe_details[key] = '[REDACTED]'
                else:
                    safe_details[key] = value
            log_data['details'] = safe_details
        
        # Log at appropriate level
        if level.upper() == 'ERROR':
            logger.error(f"Security Event: {log_data}")
        elif level.upper() == 'INFO':
            logger.info(f"Security Event: {log_data}")
        else:
            logger.warning(f"Security Event: {log_data}")
    
    @staticmethod
    def log_request_info(request, exclude_paths: List[str] = None) -> Dict[str, Any]:
        """
        Extract safe information from request for logging
        """
        if exclude_paths is None:
            exclude_paths = ['/admin/jsi18n/', '/static/', '/media/']
            
        path = getattr(request, 'path', '')
        if any(excluded in path for excluded in exclude_paths):
            return {}  # Don't log static/admin JS requests
            
        safe_info = {
            'method': getattr(request, 'method', 'UNKNOWN'),
            'path': path,
            'user_id': getattr(getattr(request, 'user', None), 'id', None),
            'ip_address': AuditSecurityLogger._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:100],  # Limit length
        }
        
        # Add query parameters but filter out sensitive ones
        query_params = getattr(request, 'GET', {})
        if query_params:
            safe_query = {}
            sensitive_params = ['password', 'token', 'key', 'secret', 'api_key']
            for key, value in query_params.items():
                if any(sensitive in key.lower() for sensitive in sensitive_params):
                    safe_query[key] = '[REDACTED]'
                else:
                    safe_query[key] = value
            safe_info['query_params'] = safe_query
            
        return safe_info
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Get client IP address from request, handling proxies
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


class SessionSecurity:
    """
    Session security utilities
    """
    
    @staticmethod
    def validate_session_timeout(request, timeout_minutes: int = 30) -> bool:
        """
        Check if session has expired based on custom timeout
        """
        if not hasattr(request, 'session'):
            return False
            
        last_activity = request.session.get('last_activity')
        if not last_activity:
            # Set initial activity time
            request.session['last_activity'] = timezone.now().timestamp()
            return True
            
        from django.utils import timezone
        now = timezone.now().timestamp()
        if (now - last_activity) > (timeout_minutes * 60):
            # Session expired
            return False
            
        # Update last activity
        request.session['last_activity'] = now
        return True
    
    @staticmethod
    def secure_session_cookie_settings() -> Dict[str, Any]:
        """
        Get secure session cookie settings
        """
        return {
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SECURE': not getattr(settings, 'DEBUG', True),  # Secure in production
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'SESSION_EXPIRE_AT_BROWSER_CLOSE': True,
            'SESSION_COOKIE_AGE': 1800,  # 30 minutes
        }


def apply_input_validation_to_dict(data: Dict[str, Any], validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Apply validation and sanitization to a dictionary of data
    validation_rules format:
    {
        'field_name': {
            'type': 'email|username|etc',
            'required': True/False,
            'sanitize': True/False,
            'max_length': int
        }
    }
    Returns sanitized data dict
    Raises ValidationError for validation failures
    """
    sanitized_data = {}
    
    for field_name, rules in validation_rules.items():
        value = data.get(field_name)
        
        # Check if required
        if rules.get('required', False) and (value is None or value == ''):
            raise ValidationError(f"{field_name} is required")
            
        # Skip validation if empty and not required
        if value is None or value == '':
            if not rules.get('required', False):
                continue
                
        # Type validation
        if 'type' in rules:
            if not InputValidator.validate_input(value, rules['type'], field_name):
                raise ValidationError(f"{field_name} has invalid format")
                
        # Length validation
        if 'max_length' in rules and value:
            if len(str(value)) > rules['max_length']:
                raise ValidationError(f"{field_name} exceeds maximum length of {rules['max_length']}")
                
        # Sanitization
        if rules.get('sanitize', False) and isinstance(value, str):
            # Apply HTML sanitization by default for string fields
            value = InputValidator.sanitize_html(value)
            
            # Additional SQL injection prevention as extra layer
            value = InputValidator.prevent_sql_injection(value)
            
        sanitized_data[field_name] = value
        
    return sanitized_data


# Example usage decorator for views
def require_jwt_authentication(view_func):
    """
    Decorator to require JWT authentication for Django views (not DRF)
    """
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                raise ValueError()
        except ValueError:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)
            
        # Validate token
        try:
            from .authentication import verify_jwt_token
            payload = verify_jwt_token(token)
            # Attach user info to request
            request.jwt_user = payload
        except Exception as e:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Invalid or expired token'}, status=401)
            
        return view_func(request, *args, **kwargs)
    return wrapper
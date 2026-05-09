"""
Base Exception Classes
Defines the base exception for the Pharmacy ERP application and common derived exceptions.
"""

class PharmacyERPException(Exception):
    """Base exception for all Pharmacy ERP application errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ValidationException(PharmacyERPException):
    """Exception raised for input validation errors."""
    
    def __init__(self, message: str, field: str = None, error_code: str = "VALIDATION_ERROR", details: dict = None):
        """
        Initialize the validation exception.
        
        Args:
            message: Human-readable error message
            field: The field that failed validation (optional)
            error_code: Machine-readable error code (default: VALIDATION_ERROR)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, error_code, details)
        self.field = field
        if field and details is not None:
            self.details['field'] = field


class DatabaseException(PharmacyERPException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR", details: dict = None):
        """
        Initialize the database exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (default: DATABASE_ERROR)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, error_code, details)


class ServiceException(PharmacyERPException):
    """Exception raised for service layer errors."""
    
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", details: dict = None):
        """
        Initialize the service exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (default: SERVICE_ERROR)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, error_code, details)


class ConfigurationException(PharmacyERPException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, error_code: str = "CONFIGURATION_ERROR", details: dict = None):
        """
        Initialize the configuration exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (default: CONFIGURATION_ERROR)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, error_code, details)
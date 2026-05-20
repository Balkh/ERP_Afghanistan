"""
API Error Codes Registry.
Standardized error codes for all modules.
"""


class ErrorCode:
    """Base class for error codes."""
    
    # Authentication errors (AUTH_xxx)
    AUTH_001 = "AUTH_001"  # Invalid credentials
    AUTH_002 = "AUTH_002"  # Token expired
    AUTH_003 = "AUTH_003"  # Unauthorized access
    AUTH_004 = "AUTH_004"  # User disabled
    AUTH_005 = "AUTH_005"  # Company not accessible
    AUTH_006 = "AUTH_006"  # Invalid refresh token
    AUTH_007 = "AUTH_007"  # Token already blacklisted
    AUTH_008 = "AUTH_008"  # 2FA setup required
    AUTH_009 = "AUTH_009"  # 2FA code required
    AUTH_010 = "AUTH_010"  # Rate limit exceeded

    # Financial/Accounting errors (FIN_xxx)
    FIN_001 = "FIN_001"  # Journal entry imbalance (debit != credit)
    FIN_002 = "FIN_002"  # Currency conversion error
    FIN_003 = "FIN_003"  # Account not found
    FIN_004 = "FIN_004"  # Journal entry already posted
    FIN_005 = "FIN_005"  # Cannot reverse posted entry
    FIN_006 = "FIN_006"  # Insufficient account balance
    FIN_007 = "FIN_007"  # Invalid account type for transaction

    # Inventory errors (INV_xxx)
    INV_001 = "INV_001"  # Insufficient stock
    INV_002 = "INV_002"  # Stock allocation failed
    INV_003 = "INV_003"  # Product not found
    INV_004 = "INV_004"  # Batch not found or expired
    INV_005 = "INV_005"  # Warehouse not found
    INV_006 = "INV_006"  # Negative quantity not allowed
    INV_007 = "INV_007"  # Duplicate batch number
    INV_008 = "INV_008"  # FEFO/FIFO order unavailable

    # Sales errors (SAL_xxx)
    SAL_001 = "SAL_001"  # Customer not found
    SAL_002 = "SAL_002"  # Invoice not found
    SAL_003 = "SAL_003"  # Invoice already confirmed/dispatched
    SAL_004 = "SAL_004"  # Cannot cancel dispatched invoice
    SAL_005 = "SAL_005"  # Payment exceeds invoice amount
    SAL_006 = "SAL_006"  # Credit limit exceeded

    # Purchase errors (PUR_xxx)
    PUR_001 = "PUR_001"  # Supplier not found
    PUR_002 = "PUR_002"  # Purchase invoice not found
    PUR_003 = "PUR_003"  # Invoice already received
    PUR_004 = "PUR_004"  # Cannot cancel received invoice
    PUR_005 = "PUR_005"  # Received quantity exceeds ordered

    # Multi-company errors (TEN_xxx)
    TEN_001 = "TEN_001"  # Company not found
    TEN_002 = "TEN_002"  # Company access denied
    TEN_003 = "TEN_003"  # Cross-company data access attempt

    # Validation errors (VAL_xxx)
    VAL_001 = "VAL_001"  # Required field missing
    VAL_002 = "VAL_002"  # Invalid field format
    VAL_003 = "VAL_003"  # Duplicate entry
    VAL_004 = "VAL_004"  # Value out of range

    # System errors (SYS_xxx)
    SYS_001 = "SYS_001"  # Internal server error
    SYS_002 = "SYS_002"  # Database connection error
    SYS_003 = "SYS_003"  # External service unavailable
    SYS_004 = "SYS_004"  # Rate limit exceeded

    # Permission errors (PER_xxx)
    PER_001 = "PER_001"  # Insufficient permissions
    PER_002 = "PER_002"  # Role not found
    PER_003 = "PER_003"  # Permission denied for resource


ERROR_MESSAGES = {
    # Authentication
    "AUTH_001": "Invalid username or password",
    "AUTH_002": "Your session has expired. Please log in again",
    "AUTH_003": "You do not have permission to access this resource",
    "AUTH_004": "Your account has been disabled. Contact administrator",
    "AUTH_005": "You do not have access to this company",
    "AUTH_006": "Invalid or expired refresh token",
    "AUTH_007": "Token has been blacklisted",
    "AUTH_008": "Your role requires 2FA. Please set up TOTP first",
    "AUTH_009": "2FA code required. Provide 'totp_code' in the request body",
    "AUTH_010": "Too many requests. Please try again later",

    # Financial
    "FIN_001": "Journal entry is imbalanced. Debits must equal credits",
    "FIN_002": "Currency conversion failed. Please check exchange rates",
    "FIN_003": "Account not found",
    "FIN_004": "Journal entry is already posted",
    "FIN_005": "Cannot reverse a posted journal entry",
    "FIN_006": "Insufficient balance in account",
    "FIN_007": "Invalid account type for this transaction",

    # Inventory
    "INV_001": "Insufficient stock available",
    "INV_002": "Failed to allocate stock. Please try again",
    "INV_003": "Product not found",
    "INV_004": "Batch not found or has expired",
    "INV_005": "Warehouse not found",
    "INV_006": "Quantity cannot be negative",
    "INV_007": "Batch number already exists",
    "INV_008": "No batches available in required order",

    # Sales
    "SAL_001": "Customer not found",
    "SAL_002": "Invoice not found",
    "SAL_003": "Invoice has already been confirmed or dispatched",
    "SAL_004": "Cannot cancel a dispatched invoice",
    "SAL_005": "Payment amount exceeds invoice total",
    "SAL_006": "Customer credit limit would be exceeded",

    # Purchases
    "PUR_001": "Supplier not found",
    "PUR_002": "Purchase invoice not found",
    "PUR_003": "Invoice has already been received",
    "PUR_004": "Cannot cancel a received invoice",
    "PUR_005": "Received quantity exceeds ordered quantity",

    # Multi-company
    "TEN_001": "Company not found",
    "TEN_002": "You do not have access to this company",
    "TEN_003": "Cross-company data access is not permitted",

    # Validation
    "VAL_001": "Required field is missing",
    "VAL_002": "Invalid format for field",
    "VAL_003": "Duplicate entry detected",
    "VAL_004": "Value is out of acceptable range",

    # System
    "SYS_001": "An internal error occurred. Please try again later",
    "SYS_002": "Database connection error",
    "SYS_003": "External service is temporarily unavailable",
    "SYS_004": "Too many requests. Please try again later",

    # Permissions
    "PER_001": "You do not have the required permission",
    "PER_002": "Role not found",
    "PER_003": "Permission denied for this resource",
}


def get_error_message(code: str) -> str:
    """Get human-readable error message for code."""
    return ERROR_MESSAGES.get(code, "An unknown error occurred")


def create_error_response(code: str, details: dict = None, custom_message: str = None):
    """Create standardized error response."""
    from core.api.responses import APIResponse
    
    message = custom_message or get_error_message(code)
    return APIResponse.error(code, message, details)


# HTTP status code mapping
ERROR_STATUS_MAP = {
    "AUTH_001": 401,
    "AUTH_002": 401,
    "AUTH_003": 403,
    "AUTH_004": 403,
    "AUTH_005": 403,
    "AUTH_006": 401,
    "AUTH_007": 401,
    "AUTH_008": 403,
    "AUTH_009": 403,
    "AUTH_010": 429,
    "FIN_001": 400,
    "FIN_002": 400,
    "FIN_003": 404,
    "FIN_004": 400,
    "FIN_005": 400,
    "FIN_006": 400,
    "FIN_007": 400,
    "INV_001": 400,
    "INV_002": 400,
    "INV_003": 404,
    "INV_004": 404,
    "INV_005": 404,
    "INV_006": 400,
    "INV_007": 400,
    "INV_008": 400,
    "SAL_001": 404,
    "SAL_002": 404,
    "SAL_003": 400,
    "SAL_004": 400,
    "SAL_005": 400,
    "SAL_006": 400,
    "PUR_001": 404,
    "PUR_002": 404,
    "PUR_003": 400,
    "PUR_004": 400,
    "PUR_005": 400,
    "TEN_001": 404,
    "TEN_002": 403,
    "TEN_003": 403,
    "VAL_001": 400,
    "VAL_002": 400,
    "VAL_003": 400,
    "VAL_004": 400,
    "SYS_001": 500,
    "SYS_002": 503,
    "SYS_003": 503,
    "SYS_004": 429,
    "PER_001": 403,
    "PER_002": 404,
    "PER_003": 403,
}


def get_status_for_error(code: str) -> int:
    """Get HTTP status code for error code."""
    return ERROR_STATUS_MAP.get(code, 400)
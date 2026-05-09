"""
Centralized constants and configuration for the Pharmacy ERP system.
"""

# Currency codes
CURRENCY_AFN = 'AFN'
CURRENCY_USD = 'USD'
CURRENCY_CHOICES = [
    (CURRENCY_AFN, 'Afghan Afghani'),
    (CURRENCY_USD, 'US Dollar'),
]

# Default currency
DEFAULT_CURRENCY = CURRENCY_AFN

# Date formats
DATE_FORMAT_GREGORIAN = '%Y-%m-%d'
DATE_FORMAT_PERSIAN = '%Y/%m/%d'

# Document number prefixes
DOC_PREFIX_SALES = 'SAL'
DOC_PREFIX_PURCHASE = 'PUR'
DOC_PREFIX_INVOICE = 'INV'
DOC_PREFIX_RECEIPT = 'REC'
DOC_PREFIX_PAYMENT = 'PAY'

# License types
LICENSE_TYPE_PERPETUAL = 'perpetual'
LICENSE_TYPE_EXPIRING = 'expiring'
LICENSE_CHOICES = [
    (LICENSE_TYPE_PERPETUAL, 'Perpetual License'),
    (LICENSE_TYPE_EXPIRING, 'Expiring License'),
]

# Status choices
STATUS_DRAFT = 'draft'
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_COMPLETED = 'completed'
STATUS_CANCELLED = 'cancelled'
STATUS_REJECTED = 'rejected'
STATUS_PAID = 'paid'
STATUS_UNPAID = 'unpaid'
STATUS_PARTIALLY_PAID = 'partially_paid'

DOCUMENT_STATUS_CHOICES = [
    (STATUS_DRAFT, 'Draft'),
    (STATUS_PENDING, 'Pending'),
    (STATUS_APPROVED, 'Approved'),
    (STATUS_COMPLETED, 'Completed'),
    (STATUS_CANCELLED, 'Cancelled'),
    (STATUS_REJECTED, 'Rejected'),
]

PAYMENT_STATUS_CHOICES = [
    (STATUS_UNPAID, 'Unpaid'),
    (STATUS_PARTIALLY_PAID, 'Partially Paid'),
    (STATUS_PAID, 'Paid'),
]

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Decimal field defaults
DECIMAL_MAX_DIGITS = 12
DECIMAL_DECIMAL_PLACES = 2

# Price precision
PRICE_MAX_DIGITS = 14
PRICE_DECIMAL_PLACES = 2
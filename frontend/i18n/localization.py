"""
Localization System for Enterprise UI.
Supports Persian (RTL), English, Shamsi dates, Gregorian dates, AFN/USD currency.
"""

from PySide6.QtCore import QObject, Signal
from typing import Dict, Optional
from enum import Enum
import logging
from datetime import date
import re

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    PERSIAN = "fa"
    PASHTO = "ps"


class DateFormat(Enum):
    """Date format options."""
    GREGORIAN = "gregorian"
    SHAMSI = "shamsi"
    ISO = "iso"


class LocaleManager(QObject):
    """
    Central locale management for multi-language support.
    """
    
    language_changed = Signal(str)
    direction_changed = Signal(bool)  # True for RTL
    currency_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self._current_language = Language.ENGLISH
        self._current_direction = False  # LTR by default
        self._current_currency = "AFN"
        self._date_format = DateFormat.SHAMSI
        
        self._translations: Dict[str, Dict[str, str]] = {
            'fa': self._get_persian_translations(),
            'en': self._get_english_translations()
        }
        
    @property
    def language(self) -> Language:
        """Get current language."""
        return self._current_language
    
    @property
    def is_rtl(self) -> bool:
        """Check if current language is RTL."""
        return self._current_language in [Language.PERSIAN, Language.PASHTO]
    
    @property
    def direction(self) -> bool:
        """Get layout direction (True for RTL)."""
        return self._current_direction
    
    @property
    def currency(self) -> str:
        """Get current currency code."""
        return self._current_currency
    
    def set_language(self, language: Language):
        """Set current language."""
        if self._current_language != language:
            self._current_language = language
            self._current_direction = language in [Language.PERSIAN, Language.PASHTO]
            self.language_changed.emit(language.value)
            self.direction_changed.emit(self._current_direction)
            logger.info(f"Language changed to: {language.value}")
            
    def set_currency(self, currency: str):
        """Set current currency."""
        if self._current_currency != currency:
            self._current_currency = currency
            self.currency_changed.emit(currency)
            
    def set_date_format(self, date_format: DateFormat):
        """Set date format."""
        self._date_format = date_format
        
    def translate(self, key: str, default: str = "") -> str:
        """Translate key to current language."""
        lang_code = self._current_language.value
        return self._translations.get(lang_code, {}).get(key, default or key)
    
    def _get_persian_translations(self) -> Dict[str, str]:
        """Get Persian translations."""
        return {
            # Navigation
            'nav.dashboard': 'داشبورد',
            'nav.inventory': 'انبارداری',
            'nav.products': 'محصولات',
            'nav.categories': 'دسته‌بندی‌ها',
            'nav.warehouses': 'انبارها',
            'nav.batches': 'بچ‌ها',
            'nav.sales': 'فروش',
            'nav.invoices': 'فاکتورها',
            'nav.customers': 'مشتریان',
            'nav.purchases': 'خرید',
            'nav.suppliers': 'تأمین‌کنندگان',
            'nav.accounting': 'حسابداری',
            'nav.chart_of_accounts': 'طرح حساب‌ها',
            'nav.journal': 'روزنامه',
            'nav.ledger': 'دفتر کل',
            'nav.reports': 'گزارش‌ها',
            'nav.trial_balance': 'تراز آزمایشی',
            'nav.profit_loss': 'سود و زیان',
            'nav.balance_sheet': 'ترازنامه',
            
            # Common
            'common.save': 'ذخیره',
            'common.cancel': 'لغو',
            'common.delete': 'حذف',
            'common.edit': 'ویرایش',
            'common.add': 'افزودن',
            'common.search': 'جستجو',
            'common.filter': 'فیلتر',
            'common.export': 'صادر',
            'common.import': 'وارد',
            'common.refresh': 'تازه‌سازی',
            'common.close': 'بستن',
            'common.back': 'بازگشت',
            'common.next': 'بعدی',
            'common.previous': 'قبلی',
            'common.yes': 'بله',
            'common.no': 'خیر',
            'common.ok': 'تأیید',
            'common.loading': 'بارگذاری...',
            'common.no_data': 'داده‌ای وجود ندارد',
            
            # Forms
            'form.required': 'این فیلد الزامی است',
            'form.invalid_email': 'ایمیل معتبر نیست',
            'form.invalid_phone': 'شماره تلفن معتبر نیست',
            'form.min_length': 'حداقل {min} کاراکتر',
            'form.max_length': 'حداکثر {max} کاراکتر',
            
            # Messages
            'msg.saved_success': 'با موفقیت ذخیره شد',
            'msg.deleted_success': 'با موفقیت حذف شد',
            'msg.error': 'خطا رخ داده است',
            'msg.confirm_delete': 'آیا مطمئن هستید؟',
            'msg.no_permission': 'دسترسی ندارید',
            
            # Validation
            'validation.required': 'الزامی',
            'validation.invalid': 'نامعتبر',
            
            # Fields
            'field.name': 'نام',
            'field.code': 'کد',
            'field.price': 'قیمت',
            'field.quantity': 'مقدار',
            'field.date': 'تاریخ',
            'field.description': 'توضیحات',
            'field.status': 'وضعیت',
            'field.total': 'مجموع',
            'field.subtotal': 'زیر مجموع',
            'field.tax': 'مالیات',
            'field.discount': 'تخفیف',
            'field.balance': 'موجودی',
            'field.contact': 'تماس',
            'field.address': 'آدرس',
        }
        
    def _get_english_translations(self) -> Dict[str, str]:
        """Get English translations."""
        return {
            # Navigation
            'nav.dashboard': 'Dashboard',
            'nav.inventory': 'Inventory',
            'nav.products': 'Products',
            'nav.categories': 'Categories',
            'nav.warehouses': 'Warehouses',
            'nav.batches': 'Batches',
            'nav.sales': 'Sales',
            'nav.invoices': 'Invoices',
            'nav.customers': 'Customers',
            'nav.purchases': 'Purchases',
            'nav.suppliers': 'Suppliers',
            'nav.accounting': 'Accounting',
            'nav.chart_of_accounts': 'Chart of Accounts',
            'nav.journal': 'Journal',
            'nav.ledger': 'Ledger',
            'nav.reports': 'Reports',
            'nav.trial_balance': 'Trial Balance',
            'nav.profit_loss': 'Profit & Loss',
            'nav.balance_sheet': 'Balance Sheet',
            
            # Common
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.add': 'Add',
            'common.search': 'Search',
            'common.filter': 'Filter',
            'common.export': 'Export',
            'common.import': 'Import',
            'common.refresh': 'Refresh',
            'common.close': 'Close',
            'common.back': 'Back',
            'common.next': 'Next',
            'common.previous': 'Previous',
            'common.yes': 'Yes',
            'common.no': 'No',
            'common.ok': 'OK',
            'common.loading': 'Loading...',
            'common.no_data': 'No data available',
            
            # Forms
            'form.required': 'This field is required',
            'form.invalid_email': 'Invalid email address',
            'form.invalid_phone': 'Invalid phone number',
            'form.min_length': 'Minimum {min} characters',
            'form.max_length': 'Maximum {max} characters',
            
            # Messages
            'msg.saved_success': 'Saved successfully',
            'msg.deleted_success': 'Deleted successfully',
            'msg.error': 'An error occurred',
            'msg.confirm_delete': 'Are you sure?',
            'msg.no_permission': 'Permission denied',
            
            # Validation
            'validation.required': 'Required',
            'validation.invalid': 'Invalid',
            
            # Fields
            'field.name': 'Name',
            'field.code': 'Code',
            'field.price': 'Price',
            'field.quantity': 'Quantity',
            'field.date': 'Date',
            'field.description': 'Description',
            'field.status': 'Status',
            'field.total': 'Total',
            'field.subtotal': 'Subtotal',
            'field.tax': 'Tax',
            'field.discount': 'Discount',
            'field.balance': 'Balance',
            'field.contact': 'Contact',
            'field.address': 'Address',
        }


class DateFormatter:
    """Date formatting utilities."""
    
    # Persian/Jalali month names
    PERSIAN_MONTHS = [
        'Farvardin', 'Ordibehesht', 'Khordad', 'Tir', 'Mordad', 'Shahrivar',
        'Mehr', 'Aban', 'Azar', 'Dey', 'Bahman', 'Esfand'
    ]
    
    PERSIAN_MONTHS_FA = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    @staticmethod
    def gregorian_to_shamsi(year: int, month: int, day: int) -> tuple:
        """Convert Gregorian date to Shamsi (Jalali)."""
        # Algorithm for Gregorian to Jalali conversion
        ge_year, ge_month, ge_day = year, month, day
        
        # Days passed since start of Gregorian year
        days = DateFormatter._days_since_start(ge_year, ge_month, ge_day)
        
        # Jalali year starts on March 21 (or 20) of Gregorian year
        if ge_month < 3 or (ge_month == 3 and ge_day < 21):
            jy = ge_year - 1
            days += DateFormatter._days_in_year(ge_year - 1)
        else:
            jy = ge_year
            
        # Find day number in Jalali year
        depoch = days - 79
        
        if depoch < 0:
            depoch += 400 * 366
            
        jy += depoch // 365
        depoch = depoch % 365
        
        if depoch < 186:
            jm = depoch // 31
            jd = depoch % 31 + 1
        else:
            jm = (depoch - 186) // 30
            jd = (depoch - 186) % 30 + 1
            
        return jy, jm + 1, jd
    
    @staticmethod
    def _days_since_start(year: int, month: int, day: int) -> int:
        """Calculate days since start of year."""
        days = day
        for m in range(1, month):
            days += DateFormatter._days_in_month(year, m)
        return days
    
    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        """Get days in month."""
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            if year % 4 == 0:
                return 29
            return 28
        return 30
    
    @staticmethod
    def _days_in_year(year: int) -> int:
        """Get days in year."""
        if year % 4 == 0:
            return 366
        return 365
    
    @staticmethod
    def format_shamsi(date_obj: date) -> str:
        """Format date as Shamsi string."""
        jy, jm, jd = DateFormatter.gregorian_to_shamsi(
            date_obj.year, date_obj.month, date_obj.day
        )
        return f"{jy}/{jm:02d}/{jd:02d}"
    
    @staticmethod
    def format_gregorian(date_obj: date) -> str:
        """Format date as Gregorian string."""
        return date_obj.strftime("%Y-%m-%d")
    
    @staticmethod
    def format(date_obj: date, format_type: DateFormat = DateFormat.SHAMSI) -> str:
        """Format date based on format type."""
        if format_type == DateFormat.SHAMSI:
            return DateFormatter.format_shamsi(date_obj)
        elif format_type == DateFormat.GREGORIAN:
            return DateFormatter.format_gregorian(date_obj)
        elif format_type == DateFormat.ISO:
            return date_obj.isoformat()
        return str(date_obj)


class CurrencyFormatter:
    """Currency formatting utilities."""
    
    CURRENCY_SYMBOLS = {
        'AFN': '؋',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    CURRENCY_NAMES = {
        'AFN': 'Afghani',
        'USD': 'US Dollar',
        'EUR': 'Euro',
        'GBP': 'British Pound'
    }
    
    @staticmethod
    def format(amount: float, currency: str = 'AFN', show_symbol: bool = True) -> str:
        """Format amount with currency."""
        symbol = CurrencyFormatter.CURRENCY_SYMBOLS.get(currency, currency)
        
        # Format number with thousand separators
        formatted = f"{amount:,.2f}"
        
        if show_symbol:
            return f"{symbol}{formatted}"
        return formatted
    
    @staticmethod
    def parse(amount_str: str) -> float:
        """Parse currency string to float."""
        # Remove currency symbols and separators
        cleaned = re.sub(r'[^\d.-]', '', amount_str)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0


class Translate:
    """
    Translation function for easy access in UI.
    Usage: tr("common.save") -> "Save" or "ذخیره"
    """
    
    _instance: Optional[LocaleManager] = None
    
    @classmethod
    def set_instance(cls, instance: LocaleManager):
        """Set global locale manager instance."""
        cls._instance = instance
        
    @classmethod
    def t(cls, key: str, default: str = "") -> str:
        """Translate key."""
        if cls._instance:
            return cls._instance.translate(key, default)
        return default or key
        
    @classmethod
    def tr(cls, key: str) -> str:
        """Translate key (alias)."""
        return cls.t(key, key)


# Global locale manager
_global_locale_manager: Optional[LocaleManager] = None

def get_locale_manager() -> LocaleManager:
    """Get global locale manager."""
    global _global_locale_manager
    if _global_locale_manager is None:
        _global_locale_manager = LocaleManager()
        Translate.set_instance(_global_locale_manager)
    return _global_locale_manager

def tr(key: str, default: str = "") -> str:
    """Quick translation function."""
    return get_locale_manager().translate(key, default)

def format_date(date_obj: date, format_type: DateFormat = DateFormat.SHAMSI) -> str:
    """Format date."""
    return DateFormatter.format(date_obj, format_type)

def format_currency(amount: float, currency: str = 'AFN', show_symbol: bool = True) -> str:
    """Format currency."""
    return CurrencyFormatter.format(amount, currency, show_symbol)
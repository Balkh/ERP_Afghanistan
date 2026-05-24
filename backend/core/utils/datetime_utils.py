"""
Datetime utilities for the ERP system.
"""
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from django.utils import timezone


def now() -> datetime:
    """Get current datetime in timezone-aware format."""
    return timezone.now()


def today() -> date:
    """Get today's date."""
    return now().date()


def start_of_day(dt: Optional[datetime] = None) -> datetime:
    """Get start of day (00:00:00) for given datetime."""
    dt = dt or now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: Optional[datetime] = None) -> datetime:
    """Get end of day (23:59:59) for given datetime."""
    dt = dt or now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_month(dt: Optional[datetime] = None) -> datetime:
    """Get first day of month at 00:00:00."""
    dt = dt or now()
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def end_of_month(dt: Optional[datetime] = None) -> datetime:
    """Get last day of month at 23:59:59."""
    dt = dt or now()
    if dt.month == 12:
        return dt.replace(day=31, hour=23, minute=59, second=59, microsecond=999999)
    next_month = dt.replace(month=dt.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return last_day.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_fiscal_year(dt: Optional[datetime] = None, fiscal_start_month: int = 1) -> int:
    """Get fiscal year for given date."""
    dt = dt or now()
    if dt.month >= fiscal_start_month:
        return dt.year
    return dt.year - 1


def get_date_range(days: int, end_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Get date range ending at end_date (or now) for given number of days."""
    end = end_date or now()
    start = end - timedelta(days=days - 1)
    return start_of_day(start), end_of_day(end)


def format_date(dt: Optional[datetime] = None, fmt: str = '%Y-%m-%d') -> str:
    """Format datetime to string."""
    dt = dt or now()
    return dt.strftime(fmt)


def parse_date(date_str: str, fmt: str = '%Y-%m-%d') -> datetime:
    """Parse date string to datetime."""
    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)


# ── Jalali (Shamsi) Date Utilities ──────────────────────────────

def gregorian_to_jalali(dt: Optional[datetime] = None) -> tuple:
    """Convert Gregorian datetime to Jalali (year, month, day) tuple."""
    from jdatetime import GregorianToJalali
    dt = dt or now()
    g2j = GregorianToJalali(dt.year, dt.month, dt.day)
    return g2j.getJalaliList()


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    """Convert Jalali date to Gregorian date."""
    from jdatetime import JalaliToGregorian
    j2g = JalaliToGregorian(jy, jm, jd)
    return date(*j2g.getGregorianList())


def today_jalali() -> tuple:
    """Get today's date as Jalali (year, month, day) tuple."""
    return gregorian_to_jalali(now())


def format_date_jalali(dt: Optional[datetime] = None, sep: str = '/') -> str:
    """Format datetime as Jalali string (e.g. 1403/04/15)."""
    dt = dt or now()
    jy, jm, jd = gregorian_to_jalali(dt)
    return f"{jy}{sep}{jm:02d}{sep}{jd:02d}"


def parse_jalali_date(date_str: str, sep: str = '/') -> datetime:
    """Parse Jalali date string to Gregorian datetime."""
    parts = date_str.split(sep)
    if len(parts) != 3:
        raise ValueError(f"Cannot parse Jalali date: {date_str}")
    jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
    g = jalali_to_gregorian(jy, jm, jd)
    return datetime.combine(g, datetime.min.time()).replace(tzinfo=timezone.utc)
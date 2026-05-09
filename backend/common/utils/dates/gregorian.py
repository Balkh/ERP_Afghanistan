"""
Gregorian Date Utilities
Provides additional functions for working with Gregorian calendar dates.
"""

from datetime import date, datetime, timedelta
from typing import Union, Optional

def add_days(g_date: Union[date, datetime], days: int) -> Union[date, datetime]:
    """
    Add days to a date.
    
    Args:
        g_date: Date to add days to
        days: Number of days to add (can be negative)
        
    Returns:
        New date after adding days
    """
    return g_date + timedelta(days=days)


def add_months(g_date: Union[date, datetime], months: int) -> Union[date, datetime]:
    """
    Add months to a date.
    
    Args:
        g_date: Date to add months to
        months: Number of months to add (can be negative)
        
    Returns:
        New date after adding months
    """
    # Handle month/year overflow
    month = g_date.month - 1 + months
    year = g_date.year + month // 12
    month = month % 12 + 1
    day = min(g_date.day, [31,
                           29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    
    if isinstance(g_date, datetime):
        return datetime(year, month, day, g_date.hour, g_date.minute, g_date.second, g_date.microsecond)
    else:
        return date(year, month, day)


def add_years(g_date: Union[date, datetime], years: int) -> Union[date, datetime]:
    """
    Add years to a date.
    
    Args:
        g_date: Date to add years to
        years: Number of years to add (can be negative)
        
    Returns:
        New date after adding years
    """
    try:
        # Try to keep the same month/day
        new_date = g_date.replace(year=g_date.year + years)
    except ValueError:
        # Handle Feb 29 on leap years
        if g_date.month == 2 and g_date.day == 29:
            new_date = date(g_date.year + years, 2, 28)
            if isinstance(g_date, datetime):
                new_date = datetime(new_date.year, new_date.month, new_date.day,
                                  g_date.hour, g_date.minute, g_date.second, g_date.microsecond)
        else:
            raise
    return new_date


def days_between(start_date: Union[date, datetime], end_date: Union[date, datetime]) -> int:
    """
    Calculate the number of days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Number of days (positive if end_date > start_date)
    """
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    return (end_date - start_date).days


def is_leap_year(year: int) -> bool:
    """
    Check if a year is a leap year.
    
    Args:
        year: Year to check
        
    Returns:
        True if leap year, False otherwise
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def get_days_in_month(year: int, month: int) -> int:
    """
    Get the number of days in a month.
    
    Args:
        year: Year
        month: Month (1-12)
        
    Returns:
        Number of days in the month
    """
    if month == 2:
        return 29 if is_leap_year(year) else 28
    return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1]


def format_date(g_date: Union[date, datetime], format_str: str = "%Y/%m/%d") -> str:
    """
    Format a Gregorian date as a string.
    
    Args:
        g_date: Date to format
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Formatted date string
    """
    if isinstance(g_date, datetime):
        g_date = g_date.date()
    return g_date.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%Y/%m/%d") -> date:
    """
    Parse a string into a Gregorian date.
    
    Args:
        date_str: Date string to parse
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Gregorian date object
    """
    return datetime.strptime(date_str, format_str).date()


def today() -> date:
    """
    Get today's date.
    
    Returns:
        Today's date
    """
    return date.today()


def now() -> datetime:
    """
    Get current date and time.
    
    Returns:
        Current datetime
    """
    return datetime.now()
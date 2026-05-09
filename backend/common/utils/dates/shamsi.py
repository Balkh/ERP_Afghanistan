"""
Shamsi (Persian) Date Utilities
Provides functions for working with Shamsi (Persian) calendar dates.
"""

import jdatetime
from datetime import date, datetime
from typing import Union, Tuple

def shamsi_to_gregorian(shamsi_date: Union[jdatetime.date, Tuple[int, int, int]]) -> date:
    """
    Convert a Shamsi date to Gregorian date.
    
    Args:
        shamsi_date: Either a jdatetime.date object or a tuple (year, month, day)
        
    Returns:
        Gregorian date as a datetime.date object
    """
    if isinstance(shamsi_date, tuple):
        year, month, day = shamsi_date
        j_date = jdatetime.date(year, month, day)
    else:
        j_date = shamsi_date
    
    return j_date.togregorian()


def gregorian_to_shamsi(gregorian_date: Union[date, datetime, Tuple[int, int, int]]) -> jdatetime.date:
    """
    Convert a Gregorian date to Shamsi date.
    
    Args:
        gregorian_date: Either a datetime.date/datetime object or a tuple (year, month, day)
        
    Returns:
        Shamsi date as a jdatetime.date object
    """
    if isinstance(gregorian_date, tuple):
        year, month, day = gregorian_date
        g_date = date(year, month, day)
    elif isinstance(gregorian_date, datetime):
        g_date = gregorian_date.date()
    else:
        g_date = gregorian_date
    
    return jdatetime.date.fromgregorian(date=g_date)


def format_shamsi_date(shamsi_date: Union[jdatetime.date, Tuple[int, int, int]], 
                      format_str: str = "%Y/%m/%d") -> str:
    """
    Format a Shamsi date as a string.
    
    Args:
        shamsi_date: Either a jdatetime.date object or a tuple (year, month, day)
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Formatted Shamsi date string
    """
    if isinstance(shamsi_date, tuple):
        year, month, day = shamsi_date
        j_date = jdatetime.date(year, month, day)
    else:
        j_date = shamsi_date
    
    return j_date.strftime(format_str)


def format_gregorian_date(gregorian_date: Union[date, datetime, Tuple[int, int, int]], 
                         format_str: str = "%Y/%m/%d") -> str:
    """
    Format a Gregorian date as a string.
    
    Args:
        gregorian_date: Either a datetime.date/datetime object or a tuple (year, month, day)
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Formatted Gregorian date string
    """
    if isinstance(gregorian_date, tuple):
        year, month, day = gregorian_date
        g_date = date(year, month, day)
    elif isinstance(gregorian_date, datetime):
        g_date = gregorian_date.date()
    else:
        g_date = gregorian_date
    
    return g_date.strftime(format_str)


def get_current_shamsi_date() -> jdatetime.date:
    """
    Get the current date in Shamsi calendar.
    
    Returns:
        Current Shamsi date
    """
    return jdatetime.date.today()


def get_current_gregorian_date() -> date:
    """
    Get the current date in Gregorian calendar.
    
    Returns:
        Current Gregorian date
    """
    return date.today()


def parse_shamsi_date(date_str: str, format_str: str = "%Y/%m/%d") -> jdatetime.date:
    """
    Parse a string into a Shamsi date.
    
    Args:
        date_str: Date string to parse
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Shamsi date object
    """
    return jdatetime.datetime.strptime(date_str, format_str).date()


def parse_gregorian_date(date_str: str, format_str: str = "%Y/%m/%d") -> date:
    """
    Parse a string into a Gregorian date.
    
    Args:
        date_str: Date string to parse
        format_str: Format string (default: "%Y/%m/%d")
        
    Returns:
        Gregorian date object
    """
    return datetime.strptime(date_str, format_str).date()
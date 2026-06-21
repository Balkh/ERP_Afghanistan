"""
Jalali (Shamsi) Calendar System for ERP Afghanistan.

Provides:
  - JalaliDateEdit: QDateEdit replacement with Jalali calendar popup
  - DateConverter: bidirectional Gregorian ↔ Jalali conversion
  - DateFormatManager: singleton that reads user's date_format preference
    and provides formatted strings globally

Uses the `jdatetime` library for accurate conversion.
"""

import logging
from datetime import date, datetime

import jdatetime
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.constants import (
    BORDER_RADIUS_MD,
    COLOR_BG_INPUT,
    COLOR_BG_SURFACE,
    COLOR_BORDER,
    COLOR_BORDER_FOCUS,
    COLOR_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_ON_PRIMARY,
    COLOR_TEXT_PRIMARY,
    FONT_FAMILY_PRIMARY,
    INPUT_HEIGHT_MD,
    SPACING_SM,
    SPACING_MD,
)

logger = logging.getLogger(__name__)

# ── Jalali month names ────────────────────────────────────────
JALALI_MONTHS_EN = [
    "Hamal", "Sawr", "Jawza", "Saratan", "Asad", "Sunbula",
    "Mizan", "Aqrab", "Qaws", "Jadi", "Dalw", "Hut",
]

JALALI_MONTHS_FA = [
    "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
    "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت",
]

JALALI_MONTHS_DARI = [
    "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
    "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت",
]

JALALI_MONTHS_PASHTO = [
    "وری", "غوی", "غبرګولی", "چنګاښ", "زمری", "وږی",
    "تله", "لړم", "لیندۍ", "مرغومی", "سلواغه", "کب",
]


# ══════════════════════════════════════════════════════════════
# DateConverter — bidirectional conversion using jdatetime
# ══════════════════════════════════════════════════════════════

class DateConverter:
    """Stateless converter between Gregorian and Jalali dates.

    All public methods accept/return plain Python ``date`` objects
    or ``jdatetime.jdatetime`` / ``jdatetime.jdate`` objects.
    """

    @staticmethod
    def gregorian_to_jalali(d: date) -> "jdatetime.date":
        """Convert a ``datetime.date`` to ``jdatetime.jdate``."""
        return jdatetime.date.fromgregorian(date=d)

    @staticmethod
    def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
        """Convert Jalali year/month/day to ``datetime.date``."""
        j = jdatetime.date(jy, jm, jd)
        return j.togregorian()

    @staticmethod
    def today_jalali() -> "jdatetime.date":
        """Return today's date in Jalali."""
        return jdatetime.date.today()

    @staticmethod
    def format_jalali(d: date, sep: str = "/") -> str:
        """Format a Gregorian date as Jalali string, e.g. ``1404/03/28``."""
        j = DateConverter.gregorian_to_jalali(d)
        return f"{j.year}{sep}{j.month:02d}{sep}{j.day:02d}"

    @staticmethod
    def format_gregorian(d: date, sep: str = "-") -> str:
        """Format a Gregorian date, e.g. ``2025-06-18``."""
        return f"{d.year}{sep}{d.month:02d}{sep}{d.day:02d}"

    @staticmethod
    def jalali_str_to_date(jalali_str: str, sep: str = "/") -> date:
        """Parse a Jalali date string (``1404/03/28``) to ``datetime.date``."""
        parts = jalali_str.split(sep)
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
        return DateConverter.jalali_to_gregorian(jy, jm, jd)

    @staticmethod
    def qdate_to_jalali_str(qdate: QDate, sep: str = "/") -> str:
        """Convert QDate to Jalali display string."""
        d = date(qdate.year(), qdate.month(), qdate.day())
        return DateConverter.format_jalali(d, sep)

    @staticmethod
    def jalali_str_to_qdate(jalali_str: str, sep: str = "/") -> QDate:
        """Convert Jalali string to QDate."""
        d = DateConverter.jalali_str_to_date(jalali_str, sep)
        return QDate(d.year, d.month, d.day)


# ══════════════════════════════════════════════════════════════
# DateFormatManager — global date-format preference
# ══════════════════════════════════════════════════════════════

class DateFormatManager:
    """Singleton that tracks the user's preferred date format.

    The preference is read from settings (``'shamsi'`` or ``'gregorian'``)
    and all screens call ``DateFormatManager.instance().format_date(d)``
    to get the correct display string.

    When the user changes the preference in Settings, call
    ``set_date_format('shamsi' | 'gregorian')`` and all listeners
    are notified.
    """

    _instance = None

    def __init__(self):
        self._date_format: str = "shamsi"  # default for Afghanistan
        self._listeners = []

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = DateFormatManager()
        return cls._instance

    @property
    def date_format(self) -> str:
        return self._date_format

    @property
    def is_jalali(self) -> bool:
        return self._date_format == "shamsi"

    def set_date_format(self, fmt: str):
        """Set format and notify listeners. ``fmt`` is ``'shamsi'`` or ``'gregorian'``."""
        old = self._date_format
        self._date_format = fmt
        if old != fmt:
            for fn in self._listeners:
                try:
                    fn(fmt)
                except Exception as e:
                    logger.warning(f"DateFormatManager listener error: {e}")

    def register_listener(self, fn):
        """Register a callback ``fn(new_format)`` called when format changes."""
        self._listeners.append(fn)

    def unregister_listener(self, fn):
        self._listeners = [l for l in self._listeners if l != fn]

    def format_date(self, d: date, fmt: str = None) -> str:
        """Format a date using the active (or explicitly given) format."""
        use_jalali = (fmt or self._date_format) == "shamsi"
        if use_jalali:
            return DateConverter.format_jalali(d)
        return DateConverter.format_gregorian(d)

    def format_datetime(self, dt: datetime, fmt: str = None) -> str:
        """Format a datetime; appends HH:MM if available."""
        base = self.format_date(dt.date(), fmt)
        if dt.hour or dt.minute:
            base += f" {dt.hour:02d}:{dt.minute:02d}"
        return base


# ══════════════════════════════════════════════════════════════
# JalaliCalendarWidget — QCalendarWidget with Jalali rendering
# ══════════════════════════════════════════════════════════════

class JalaliCalendarWidget(QCalendarWidget):
    """A QCalendarWidget that shows Jalali month/year in the header.

    Internally uses the Gregorian calendar (Qt's native) but converts
    the displayed month/year to Jalali.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_styles()
        # Update header text on page change
        self.currentPageChanged.connect(self._update_header_text)
        self._update_header_text()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
            }}
            QCalendarWidget QToolButton {{
                color: {COLOR_TEXT_PRIMARY};
                background-color: {COLOR_BG_SURFACE};
                border: none;
                padding: {SPACING_SM}px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
                border-radius: {BORDER_RADIUS_MD}px;
            }}
            QCalendarWidget QMenu {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY};
                selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: none;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {COLOR_BG_SURFACE};
            }}
        """)

    def _update_header_text(self):
        """Override the month/year display with Jalali equivalent."""
        year = self.yearShown()
        month = self.monthShown()
        g = date(year, month, 1)
        j = DateConverter.gregorian_to_jalali(g)
        # Find month name
        month_name = JALALI_MONTHS_DARI[j.month - 1] if j.month <= 12 else ""
        header = f"{month_name} {j.year}"
        # Set the header text via stylesheet on the navigation bar
        navbar = self.findChild(QWidget, "qt_calendar_navigationbar")
        if navbar:
            for btn in navbar.findChildren(QWidget):
                if hasattr(btn, 'setText') and hasattr(btn, 'text'):
                    current = btn.text()
                    if current and any(c.isdigit() for c in current):
                        btn.setText(header)


# ══════════════════════════════════════════════════════════════
# JalaliDateEdit — drop-in QDateEdit replacement
# ══════════════════════════════════════════════════════════════

class JalaliDateEdit(QDateEdit):
    """A date editor that displays dates in Jalali (Shamsi) format.

    - Internally stores Gregorian QDate (database/API compatible)
    - Displays in Jalali format when DateFormatManager is set to 'shamsi'
    - Calendar popup shows Jalali month names
    - Seamless toggle between Gregorian and Jalali display
    """

    def __init__(self, parent=None, date_format: str = None):
        super().__init__(parent)
        self._override_format = date_format  # None = follow global
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")  # Gregorian default
        self.setDate(QDate.currentDate())
        self.setMinimumHeight(INPUT_HEIGHT_MD)

        # Replace calendar with Jalali-aware one
        self._jalali_calendar = JalaliCalendarWidget(self)
        self.setCalendarWidget(self._jalali_calendar)

        # Listen to global format changes
        self._mgr = DateFormatManager.instance()
        self._mgr.register_listener(self._on_format_changed)
        self._apply_display_format()

    def _on_format_changed(self, fmt: str):
        """Called when global date format preference changes."""
        if self._override_format is None:
            self._apply_display_format()

    def _apply_display_format(self):
        """Apply the correct display format based on current preference."""
        fmt = self._override_format or self._mgr.date_format
        if fmt == "shamsi":
            self.setDisplayFormat("yyyy/MM/dd")  # We override displayText
        else:
            self.setDisplayFormat("yyyy-MM-dd")

    def displayText(self) -> str:
        """Override to show Jalali date when in Shamsi mode."""
        fmt = self._override_format or self._mgr.date_format
        if fmt == "shamsi":
            qd = self.date()
            d = date(qd.year(), qd.month(), qd.day())
            return DateConverter.format_jalali(d, "/")
        return super().displayText()

    def set_jalali_date(self, jy: int, jm: int, jd: int):
        """Set the date from Jalali year/month/day."""
        g = DateConverter.jalali_to_gregorian(jy, jm, jd)
        self.setDate(QDate(g.year, g.month, g.day))

    def jalali_string(self, sep: str = "/") -> str:
        """Return the current date as Jalali string."""
        qd = self.date()
        d = date(qd.year(), qd.month(), qd.day())
        return DateConverter.format_jalali(d, sep)

    def gregorian_date(self) -> date:
        """Return the current date as Python ``datetime.date``."""
        qd = self.date()
        return date(qd.year(), qd.month(), qd.day())

    def cleanup(self):
        """Unregister from DateFormatManager to prevent memory leaks."""
        self._mgr.unregister_listener(self._on_format_changed)


# ══════════════════════════════════════════════════════════════
# DateFormatToggle — combo box for switching date display
# ══════════════════════════════════════════════════════════════

class DateFormatToggle(QComboBox):
    """A compact dropdown that lets the user switch between
    Gregorian and Jalali display for a specific screen/section.

    Options:
      - "Jalali (شمسی)"
      - "Gregorian (میلادی)"

    When changed, calls ``DateFormatManager.set_date_format()``
    which propagates to all ``JalaliDateEdit`` and formatted
    date displays globally.
    """

    _STYLESHEET = f"""
        QComboBox {{
            background-color: {COLOR_BG_INPUT};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_MD}px;
            padding: 4px 12px;
            min-height: {INPUT_HEIGHT_MD - 8}px;
            font-family: {FONT_FAMILY_PRIMARY};
        }}
        QComboBox:hover {{
            border-color: {COLOR_BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLOR_BG_SURFACE};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER};
            selection-background-color: {COLOR_PRIMARY};
            selection-color: {COLOR_TEXT_ON_PRIMARY};
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(["Jalali (شمسی)", "Gregorian (میلادی)"])
        self.setStyleSheet(self._STYLESHEET)

        mgr = DateFormatManager.instance()
        if mgr.is_jalali:
            self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(1)

        self.currentIndexChanged.connect(self._on_change)

    def _on_change(self, index: int):
        fmt = "shamsi" if index == 0 else "gregorian"
        DateFormatManager.instance().set_date_format(fmt)


# ══════════════════════════════════════════════════════════════
# Helper: format a date string from API for display
# ══════════════════════════════════════════════════════════════

def format_date_for_display(date_str: str, fmt: str = None) -> str:
    """Convert an ISO date string (``'2025-06-18'``) to display format.

    Uses the global DateFormatManager preference unless ``fmt`` is given.
    Returns the original string on parse failure.
    """
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return DateFormatManager.instance().format_date(d, fmt)
    except (ValueError, TypeError):
        return date_str


def format_date_obj_for_display(d: date, fmt: str = None) -> str:
    """Format a ``datetime.date`` object for display using global preference."""
    if d is None:
        return ""
    return DateFormatManager.instance().format_date(d, fmt)

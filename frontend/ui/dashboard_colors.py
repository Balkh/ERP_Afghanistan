"""Dashboard color scheme (data-only, extracted from dashboard.py).

Phase 5 WS-D: Critical God Object Elimination.
Extracted from the Dashboard class to decouple color/scheme resolution
from UI construction. Pure data + tiny lookups; no Qt, no I/O, no
external state. Safe to import from anywhere.

The single responsibility of this module is: given a color key
(``'red'``, ``'peach'``, ``'blue'``, ``'green'``, ``'mauve'``) or a
severity name (``'critical'``, ``'warning'``, ``'info'``), return the
matching ``COLOR_*`` design token from :mod:`ui.constants`.

The default fallback for unknown keys is :data:`COLOR_PRIMARY`. The
default fallback for unknown severities is the ``'info'`` color key
(blue), matching the pre-extraction inline behavior at L438 of
``dashboard.py``.
"""
from typing import Dict

from ui.constants import (
    COLOR_DANGER,
    COLOR_INFO,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
)


class DashboardColorScheme:
    """Resolves dashboard color keys and severity names to COLOR_* tokens.

    Public surface is intentionally tiny: two class methods and three
    class-level dicts. No instance state, no Qt dependencies.
    """

    COLOR_MAP: Dict[str, str] = {
        "blue": COLOR_PRIMARY,
        "red": COLOR_DANGER,
        "green": COLOR_SUCCESS,
        "mauve": COLOR_INFO,
        "peach": COLOR_WARNING,
    }

    SEVERITY_TO_COLOR: Dict[str, str] = {
        "critical": "red",
        "warning": "peach",
        "info": "blue",
    }

    DEFAULT = COLOR_PRIMARY

    @classmethod
    def get(cls, key: str) -> str:
        """Resolve a color key to its ``COLOR_*`` token.

        Unknown keys fall back to :data:`DEFAULT` (``COLOR_PRIMARY``).
        """
        return cls.COLOR_MAP.get(key, cls.DEFAULT)

    @classmethod
    def for_severity(cls, severity: str) -> str:
        """Resolve a severity name to its ``COLOR_*`` token.

        Unknown severities fall back to the ``'info'`` color (blue),
        matching the pre-extraction inline behavior.
        """
        return cls.get(cls.SEVERITY_TO_COLOR.get(severity, "info"))

"""
Persian Localization Utilities
Provides functions for translating UI elements and handling Persian language specifics.
"""

import gettext
import os
from typing import Dict, Any

# Path to locale directory
LOCALE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'locale')

# Supported languages
LANGUAGES = {
    'fa': 'Persian',
    'en': 'English',
}

# Default language
DEFAULT_LANGUAGE = 'fa'

# Translator cache
_translators: Dict[str, Any] = {}


def get_translator(language_code: str = DEFAULT_LANGUAGE):
    """
    Get a translator for the given language code.
    Uses caching to avoid reloading the same translator multiple times.
    """
    if language_code not in _translators:
        try:
            translator = gettext.translation(
                'messages',
                localedir=LOCALE_PATH,
                languages=[language_code],
                fallback=True
            )
            _translators[language_code] = translator
        except FileNotFoundError:
            # Fallback to null translator if no translations are found
            _translators[language_code] = gettext.NullTranslations()
    return _translators[language_code]


def _(message: str, language_code: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a message to the specified language.
    Defaults to Persian (fa) if no language is specified.
    """
    translator = get_translator(language_code)
    return translator.gettext(message)


def ngettext(singular: str, plural: str, n: int, language_code: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a message with plural forms.
    """
    translator = get_translator(language_code)
    return translator.ngettext(singular, plural, n)


def pgettext(context: str, message: str, language_code: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a message with context.
    """
    translator = get_translator(language_code)
    return translator.pgettext(context, message)


def npgettext(context: str, singular: str, plural: str, n: int, language_code: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a message with context and plural forms.
    """
    translator = get_translator(language_code)
    return translator.npgettext(context, singular, plural, n)


def get_language_name(language_code: str) -> str:
    """
    Get the full name of a language from its code.
    """
    return LANGUAGES.get(language_code, language_code)


def is_rtl_language(language_code: str) -> bool:
    """
    Check if the language is right-to-left (like Persian/Arabic).
    """
    rtl_languages = ['fa', 'ar', 'he', 'ur']
    return language_code in rtl_languages


def get_supported_languages() -> Dict[str, str]:
    """
    Get a dictionary of supported language codes and their names.
    """
    return LANGUAGES.copy()


# Initialize default translator for Persian
_ = get_translator(DEFAULT_LANGUAGE).gettext
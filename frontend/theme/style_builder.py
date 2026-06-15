"""
UI Style Builder — Centralized abstraction layer for all UI component styling.
Ensures consistency, prevents theme drift, and enforces ui.constants tokens.
"""

import ui.constants as _tokens

class UIStyleBuilder:
    """
    Single authority for generating QSS stylesheets.
    Components should call these methods instead of building f-strings locally.
    """

    @staticmethod
    def get_button_style(variant: str = "primary", size: str = "medium") -> str:
        """Generate professional button styles."""
        # Mapping variants to tokens
        variant_map = {
            "primary": (_tokens.COLOR_PRIMARY, _tokens.COLOR_PRIMARY_HOVER, _tokens.COLOR_PRIMARY_ACTIVE, _tokens.COLOR_TEXT_ON_PRIMARY),
            "secondary": (_tokens.COLOR_BG_BUTTON_SECONDARY, _tokens.COLOR_BG_BUTTON_LIGHT, _tokens.COLOR_BORDER_LIGHT, _tokens.COLOR_SECONDARY_TEXT),
            "success": (_tokens.COLOR_SUCCESS, _tokens.COLOR_SUCCESS_HOVER, _tokens.COLOR_SUCCESS_ACTIVE, _tokens.COLOR_TEXT_ON_PRIMARY),
            "danger": (_tokens.COLOR_DANGER, _tokens.COLOR_DANGER_HOVER, _tokens.COLOR_DANGER_ACTIVE, _tokens.COLOR_TEXT_ON_PRIMARY),
            "warning": (_tokens.COLOR_WARNING, _tokens.COLOR_WARNING_HOVER, _tokens.COLOR_WARNING_ACTIVE, _tokens.COLOR_TEXT_ON_WARNING),
        }
        
        bg, hover, active, fg = variant_map.get(variant, variant_map["primary"])
        
        # Base style
        style = f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {bg if variant != "secondary" else _tokens.COLOR_BORDER};
                font-weight: 600;
                border-radius: {_tokens.BORDER_RADIUS_MD}px;
                padding: {_tokens.SPACING_SM}px {_tokens.SPACING_XL}px;
                font-size: {_tokens.TEXT_BODY}pt;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border: 1px solid {hover if variant != "secondary" else _tokens.COLOR_BORDER_INPUT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {active};
            }}
            QPushButton:focus {{
                border: 2px solid {_tokens.COLOR_PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {_tokens.COLOR_BG_DISABLED};
                border: 1px solid {_tokens.COLOR_BORDER_LIGHT};
                color: {_tokens.COLOR_TEXT_DISABLED};
            }}
        """
        
        if variant == "ghost":
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {_tokens.COLOR_PRIMARY};
                    border: 1px solid transparent;
                    font-weight: 600;
                    border-radius: {_tokens.BORDER_RADIUS_MD}px;
                    padding: {_tokens.SPACING_SM}px {_tokens.SPACING_XL}px;
                }}
                QPushButton:hover {{
                    background-color: {_tokens.COLOR_BG_HOVER};
                    color: {_tokens.COLOR_PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {_tokens.COLOR_BG_FOCUS};
                }}
                QPushButton:disabled {{
                    color: {_tokens.COLOR_TEXT_MUTED};
                }}
            """
            
        return style

    @staticmethod
    def get_input_style(state: str = "default") -> str:
        """Generate standard input field styles with validation support."""
        # Re-import constants for theme sync
        from ui.constants import (
            COLOR_BG_INPUT, COLOR_BORDER_INPUT, COLOR_VALID_ERROR,
            COLOR_VALID_SUCCESS, COLOR_VALID_WARNING, BORDER_RADIUS_MD,
            COLOR_TEXT_PRIMARY, TEXT_BODY, COLOR_PRIMARY_MUTED,
            COLOR_BORDER_INPUT_HOVER, COLOR_PRIMARY, COLOR_BG_SURFACE,
            COLOR_BG_MAIN, COLOR_TEXT_MUTED, COLOR_BORDER_LIGHT,
            COLOR_TEXT_SECONDARY, SPACING_SM, COLOR_BG_DISABLED,
            COLOR_TEXT_DISABLED
        )

        border_color = COLOR_BORDER_INPUT
        if state == "error":
            border_color = COLOR_VALID_ERROR
        elif state == "success":
            border_color = COLOR_VALID_SUCCESS
        elif state == "warning":
            border_color = COLOR_VALID_WARNING

        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
                background-color: {COLOR_BG_INPUT};
                border: 1px solid {border_color};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM}px {SPACING_SM}px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {TEXT_BODY}pt;
                selection-background-color: {COLOR_PRIMARY_MUTED};
                selection-color: {COLOR_TEXT_PRIMARY};
            }}
            QLineEdit:hover, QTextEdit:hover, QComboBox:hover {{
                border: 1px solid {COLOR_BORDER_INPUT_HOVER if state == "default" else border_color};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {COLOR_PRIMARY};
                background-color: {COLOR_BG_SURFACE};
            }}
            QLineEdit:disabled {{
                background-color: {COLOR_BG_DISABLED};
                color: {COLOR_TEXT_DISABLED};
                border: 1px solid {COLOR_BORDER_LIGHT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLOR_TEXT_SECONDARY};
                margin-right: 10px;
            }}
        """

    @staticmethod
    def get_tab_style() -> str:
        """Generate enterprise tab widget styles."""
        # Re-import for theme parity
        from ui.constants import (
            COLOR_BORDER, BORDER_RADIUS_LG, COLOR_BG_SURFACE,
            COLOR_BG_ELEVATED, COLOR_TEXT_SECONDARY, SPACING_MD,
            BORDER_RADIUS_MD, COLOR_PRIMARY, COLOR_BG_HOVER, COLOR_TEXT_PRIMARY,
            COLOR_TEXT_ON_PRIMARY
        )
        
        return f"""
            QTabWidget::pane {{ 
                border: 1px solid {COLOR_BORDER}; 
                border-radius: {BORDER_RADIUS_LG}px; 
                background: {COLOR_BG_SURFACE}; 
            }}
            QTabBar::tab {{ 
                background: {COLOR_BG_ELEVATED}; 
                color: {COLOR_TEXT_SECONDARY}; 
                border: none; 
                padding: {SPACING_MD}px 24px; 
                border-top-left-radius: {BORDER_RADIUS_MD}px; 
                border-top-right-radius: {BORDER_RADIUS_MD}px; 
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ 
                background: {COLOR_PRIMARY}; 
                color: {COLOR_TEXT_ON_PRIMARY}; 
                font-weight: 600; 
            }}
            QTabBar::tab:hover:!selected {{ 
                background: {COLOR_BG_HOVER}; 
                color: {COLOR_TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def get_card_style() -> str:
        """Generate card/section container styles."""
        return f"""
            QFrame#card, QWidget#card {{
                background-color: {_tokens.COLOR_BG_SURFACE};
                border: 1px solid {_tokens.COLOR_BORDER};
                border-radius: {_tokens.BORDER_RADIUS_LG}px;
            }}
        """

    @staticmethod
    def get_table_style() -> str:
        """Centralized table stylesheet builder."""
        # Re-import constants inside to ensure they are fresh
        from ui.constants import (
            TABLE_BG_PRIMARY, TABLE_BG_SECONDARY, TABLE_BG_HOVER, TABLE_BG_SELECTED,
            TABLE_GRID_COLOR, TABLE_TEXT_PRIMARY, TABLE_TEXT_SELECTED, TABLE_HEADER_BG,
            TABLE_HEADER_TEXT, TABLE_SCROLLBAR_BG, TABLE_SCROLLBAR_HANDLE, BORDER_RADIUS_SM,
            TEXT_TABLE, TEXT_TABLE_HEADER, COLOR_BORDER, COLOR_BORDER_INPUT_HOVER, COLOR_BORDER_FOCUS
        )
        
        return f"""
            QTableWidget {{
                background-color: {TABLE_BG_PRIMARY};
                alternate-background-color: {TABLE_BG_SECONDARY};
                color: {TABLE_TEXT_PRIMARY};
                gridline-color: {TABLE_GRID_COLOR};
                border: 1px solid {TABLE_GRID_COLOR};
                border-radius: {BORDER_RADIUS_SM}px;
                selection-background-color: {TABLE_BG_SELECTED};
                selection-color: {TABLE_TEXT_SELECTED};
                outline: none;
                font-size: {TEXT_TABLE}pt;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
                color: {TABLE_TEXT_PRIMARY};
                border: none;
                border-bottom: 1px solid {TABLE_GRID_COLOR};
            }}
            QTableWidget::item:selected {{
                background-color: {TABLE_BG_SELECTED};
                color: {TABLE_TEXT_SELECTED};
                font-weight: 500;
            }}
            QTableWidget::item:hover {{
                background-color: {TABLE_BG_HOVER};
            }}
            QHeaderView::section {{
                background-color: {TABLE_HEADER_BG};
                color: {TABLE_HEADER_TEXT};
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid {COLOR_BORDER};
                border-right: 1px solid {TABLE_GRID_COLOR};
                font-weight: 600;
                font-size: {TEXT_TABLE_HEADER}pt;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QScrollBar:vertical {{
                background: {TABLE_SCROLLBAR_BG};
                width: 12px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {TABLE_SCROLLBAR_HANDLE};
                min-height: 40px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLOR_BORDER_INPUT_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: {TABLE_SCROLLBAR_BG};
                height: 12px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {TABLE_SCROLLBAR_HANDLE};
                min-width: 40px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            QTableWidget:focus {{
                border: 2px solid {COLOR_BORDER_FOCUS};
            }}
        """

    @staticmethod
    def get_global_style() -> str:
        """Generate global system-level styles for QComboBox, QMenu, etc."""
        # Re-import constants for dynamic theme updates
        from ui.constants import (
            COLOR_BG_INPUT, COLOR_TEXT_PRIMARY, COLOR_BORDER, BORDER_RADIUS_MD,
            INPUT_HEIGHT_SM, TEXT_BODY, COLOR_PRIMARY, COLOR_BG_ELEVATED,
            COLOR_TEXT_ON_PRIMARY, COLOR_BG_HOVER, COLOR_BG_SURFACE
        )
        
        return f"""
            QComboBox {{
                background-color: {COLOR_BG_INPUT};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: 8px 12px;
                min-height: {INPUT_HEIGHT_SM}px;
                font-size: {TEXT_BODY}pt;
            }}
            QComboBox:hover {{
                border: 1px solid {COLOR_PRIMARY};
            }}
            QComboBox:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY};
                selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                outline: none;
                padding: 4px 0;
                font-size: {TEXT_BODY}pt;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                min-height: 28px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLOR_BG_HOVER};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
            }}
            QListView {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD}px;
                font-size: {TEXT_BODY}pt;
            }}
            QListView::item {{
                padding: 8px 12px;
                min-height: 28px;
            }}
            QListView::item:selected {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
            }}
            QMenu {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                padding: 6px 0;
                font-size: {TEXT_BODY}pt;
            }}
            QMenu::item {{
                padding: 8px 24px;
                min-height: 28px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_ON_PRIMARY};
            }}
        """

    @staticmethod
    def get_code_editor_style() -> str:
        """Generate style for code/log viewers."""
        return f"""
            QTextEdit {{
                background: {_tokens.COLOR_BG_SURFACE};
                color: {_tokens.COLOR_TEXT_PRIMARY};
                border: 1px solid {_tokens.COLOR_BORDER};
                border-radius: {_tokens.BORDER_RADIUS_MD}px;
                padding: {_tokens.SPACING_MD}px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: {_tokens.TEXT_BODY_SMALL}pt;
            }}
        """

    @staticmethod
    def get_colored_label_style(color: str, size_pt: int = 10, weight: int = 400) -> str:
        """Generate style for a label with a specific dynamic color."""
        return f"color: {color}; font-size: {size_pt}pt; font-weight: {weight};"

    @staticmethod
    def get_workflow_button_style(color: str) -> str:
        """Generate style for workflow buttons with dynamic border colors."""
        return f"""
            QPushButton {{
                background-color: {_tokens.COLOR_BG_SURFACE};
                color: {_tokens.COLOR_TEXT_PRIMARY};
                border: 2px solid {color};
                border-radius: {_tokens.BORDER_RADIUS_LG}px;
                padding: {_tokens.SPACING_LG}px 20px;
                font-size: {_tokens.TEXT_CARD_TITLE}pt;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {_tokens.COLOR_BG_HOVER};
                border: 2px solid {_tokens.COLOR_PRIMARY};
            }}
        """

    @staticmethod
    def get_label_style(role: str = "body") -> str:
        """Generate semantic label styles."""
        roles = {
            "title": f"color: {_tokens.COLOR_TEXT_PRIMARY}; font-size: {_tokens.TEXT_PAGE_TITLE}pt; font-weight: 700;",
            "section": f"color: {_tokens.COLOR_TEXT_PRIMARY}; font-size: {_tokens.TEXT_SECTION_TITLE}pt; font-weight: 600;",
            "body": f"color: {_tokens.COLOR_TEXT_PRIMARY}; font-size: {_tokens.TEXT_BODY}pt;",
            "muted": f"color: {_tokens.COLOR_TEXT_MUTED}; font-size: {_tokens.TEXT_BODY_SMALL}pt;",
            "label": f"color: {_tokens.COLOR_FORM_LABEL}; font-weight: 600; font-size: {_tokens.TEXT_LABEL}pt;",
            "error": f"color: {_tokens.COLOR_VALID_ERROR}; font-size: {_tokens.TEXT_HELPER}pt; font-weight: 500;",
            "success": f"color: {_tokens.COLOR_VALID_SUCCESS}; font-size: {_tokens.TEXT_HELPER}pt; font-weight: 500;",
            "warning": f"color: {_tokens.COLOR_VALID_WARNING}; font-size: {_tokens.TEXT_HELPER}pt; font-weight: 500;",
            "helper": f"color: {_tokens.COLOR_HELPER_TEXT_DARK}; font-size: {_tokens.TEXT_HELPER}pt; border: none; background: transparent; padding: 0; margin: 0;",
            "label_small": f"color: {_tokens.COLOR_TEXT_SECONDARY}; font-size: {_tokens.TEXT_LABEL_SMALL}pt; border: none; background: transparent; padding: 0; margin: 0; font-weight: 500;",
        }
        return roles.get(role, roles["body"])

    @staticmethod
    def get_status_indicator_style(color: str) -> str:
        """Generate style for status indicator cards."""
        # Re-import for fresh tokens
        from ui.constants import COLOR_BG_ELEVATED, BORDER_RADIUS_LG, SPACING_MD
        return f"""
            QFrame {{
                background: {COLOR_BG_ELEVATED};
                border: 2px solid {color};
                border-radius: {BORDER_RADIUS_LG}px;
                padding: {SPACING_MD}px;
            }}
        """

    @staticmethod
    def get_warning_banner_style(level: str = 'warning') -> str:
        """Generate style for warning/error banners."""
        color = _tokens.COLOR_WARNING if level == 'warning' else _tokens.COLOR_DANGER
        bg = _tokens.COLOR_WARNING_BG if level == 'warning' else _tokens.COLOR_DANGER_BG
        return f"""
            QFrame {{
                background: {bg};
                border-left: 4px solid {color};
                border-radius: {_tokens.BORDER_RADIUS_MD}px;
                padding: {_tokens.SPACING_MD}px;
            }}
        """

    @staticmethod
    def get_badge_style(color: str) -> str:
        """Generate style for state badges."""
        # Re-import for fresh tokens
        from ui.constants import COLOR_BG_ELEVATED, BORDER_RADIUS_MD, SPACING_SM
        return f"""
            QFrame {{
                background: {COLOR_BG_ELEVATED};
                border: 1px solid {color};
                border-radius: {BORDER_RADIUS_MD}px;
                padding: {SPACING_SM}px;
            }}
        """

    @staticmethod
    def get_divider_style() -> str:
        """Generate standard section divider styles."""
        return f"""
            background-color: {_tokens.COLOR_FORM_SECTION_DIVIDER};
            border: none;
            max-height: {_tokens.SECTION_DIVIDER_HEIGHT}px;
            margin: {_tokens.SPACING_SM}px 0;
        """

    @staticmethod
    def get_form_section_style(primary: bool = True) -> str:
        """Generate enterprise form section styles."""
        # Re-import constants to ensure theme sync
        from ui.constants import (
            COLOR_FORM_SECTION_TITLE, COLOR_TEXT_SECONDARY, COLOR_BG_SECTION,
            COLOR_BORDER_SECTION, BORDER_RADIUS_LG, SECTION_TITLE_SPACING,
            TEXT_CARD_TITLE, SPACING_MD, SPACING_XS
        )
        
        weight = "700" if primary else "600"
        color = COLOR_FORM_SECTION_TITLE if primary else COLOR_TEXT_SECONDARY
        
        return f"""
            QGroupBox {{
                font-size: {TEXT_CARD_TITLE}pt;
                font-weight: {weight};
                color: {color};
                background-color: {COLOR_BG_SECTION};
                border: 1px solid {COLOR_BORDER_SECTION};
                border-radius: {BORDER_RADIUS_LG}px;
                margin-top: {SECTION_TITLE_SPACING}px;
                padding-top: {SECTION_TITLE_SPACING + 6}px;
                padding-bottom: {SPACING_XS}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {SPACING_MD}px;
                color: {color};
                letter-spacing: 0.3px;
            }}
        """

    @staticmethod
    def get_state_label_style(state: str = "loading") -> str:
        """Generate style for loading/empty/error state labels.

        Centralizes the 25+ inline styles for state labels across all screens.

        Args:
            state: "loading" | "empty" | "error"
        """
        from ui.constants import (
            COLOR_TEXT_MUTED, COLOR_DANGER, TEXT_BODY, SPACING_XL, SPACING_MD
        )
        padding = SPACING_XL + SPACING_MD
        if state == "error":
            return (
                f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; "
                f"padding: {padding}px;"
            )
        return (
            f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; "
            f"padding: {padding}px;"
        )

    @staticmethod
    def get_page_header_style() -> str:
        """Generate style for page title headers."""
        return (
            f"color: {_tokens.COLOR_TEXT_PRIMARY}; "
            f"font-size: {_tokens.TEXT_PAGE_TITLE}pt; "
            f"font-weight: 700;"
        )

    @staticmethod
    def get_toolbar_style() -> str:
        """Generate style for toolbar containers."""
        return (
            f"background-color: {_tokens.COLOR_BG_MAIN}; "
            f"border: 1px solid {_tokens.COLOR_BORDER}; "
            f"border-radius: {_tokens.BORDER_RADIUS_LG}px;"
        )

    @staticmethod
    def get_subtitle_style() -> str:
        """Generate style for dialog/form subtitles."""
        return (
            f"color: {_tokens.COLOR_TEXT_MUTED}; "
            f"font-size: {_tokens.TEXT_BODY_SMALL}pt; "
            f"border: none; background: transparent; "
            f"margin-bottom: {_tokens.SPACING_SM}px;"
        )

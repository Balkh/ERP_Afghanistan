"""
Enterprise Styling System.
Provides consistent styling across all UI components.
"""

from PySide6.QtCore import QObject
from typing import Dict, Optional


class Typography:
    """Typography system for consistent text styling."""
    
    # Font families
    FONT_FAMILY_PRIMARY = "Segoe UI"
    FONT_FAMILY_SECONDARY = "Arial"
    FONT_FAMILY_MONO = "Consolas"
    
    # Font sizes (in points)
    FONT_SIZE_H1 = 24
    FONT_SIZE_H2 = 20
    FONT_SIZE_H3 = 16
    FONT_SIZE_H4 = 14
    FONT_SIZE_BODY = 11
    FONT_SIZE_SMALL = 9
    FONT_SIZE_CAPTION = 8
    
    # Font weights
    FONT_WEIGHT_BOLD = 700
    FONT_WEIGHT_SEMIBOLD = 600
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_LIGHT = 300
    
    @staticmethod
    def get_header_styles() -> Dict[str, str]:
        """Get header text styles."""
        return {
            'h1': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_H1}pt; font-weight: {Typography.FONT_WEIGHT_BOLD};",
            'h2': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_H2}pt; font-weight: {Typography.FONT_WEIGHT_BOLD};",
            'h3': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_H3}pt; font-weight: {Typography.FONT_WEIGHT_SEMIBOLD};",
            'h4': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_H4}pt; font-weight: {Typography.FONT_WEIGHT_SEMIBOLD};",
        }
    
    @staticmethod
    def get_body_styles() -> Dict[str, str]:
        """Get body text styles."""
        return {
            'body': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_BODY}pt; font-weight: {Typography.FONT_WEIGHT_NORMAL};",
            'body_small': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_SMALL}pt; font-weight: {Typography.FONT_WEIGHT_NORMAL};",
            'caption': f"font-family: {Typography.FONT_FAMILY_PRIMARY}; font-size: {Typography.FONT_SIZE_CAPTION}pt; font-weight: {Typography.FONT_WEIGHT_NORMAL};",
            'mono': f"font-family: {Typography.FONT_FAMILY_MONO}; font-size: {Typography.FONT_SIZE_BODY}pt;",
        }


class Spacing:
    """Spacing system for consistent layout."""
    
    # Spacing values (in pixels)
    SPACING_XXS = 2
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24
    SPACING_XXL = 32
    SPACING_XXXL = 48
    
    # Border radius
    BORDER_RADIUS_SM = 2
    BORDER_RADIUS_MD = 4
    BORDER_RADIUS_LG = 8
    BORDER_RADIUS_XL = 12
    
    @staticmethod
    def get_spacing_map() -> Dict[str, int]:
        """Get spacing value map."""
        return {
            'xxs': Spacing.SPACING_XXS,
            'xs': Spacing.SPACING_XS,
            'sm': Spacing.SPACING_SM,
            'md': Spacing.SPACING_MD,
            'lg': Spacing.SPACING_LG,
            'xl': Spacing.SPACING_XL,
            'xxl': Spacing.SPACING_XXL,
            'xxxl': Spacing.SPACING_XXXL,
        }


class EnterpriseStyles:
    """
    Enterprise-grade component styles.
    Provides consistent styling for all UI components.
    """

    @staticmethod
    def _lighten(hex_color: str, factor: float = 0.15) -> str:
        """Lighten a hex color by factor."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.15) -> str:
        """Darken a hex color by factor."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def get_button_styles(primary_color: str, bg_color: str, fg_color: str, 
                          border_color: str, input_bg: str) -> str:
        """Get comprehensive button styles."""
        hover = EnterpriseStyles._lighten(primary_color, 0.2)
        pressed = EnterpriseStyles._darken(primary_color, 0.15)
        return f"""
            QPushButton {{
                background-color: {primary_color};
                color: white;
                border: none;
                padding: {Spacing.SPACING_SM}px {Spacing.SPACING_LG}px;
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                font-family: {Typography.FONT_FAMILY_PRIMARY};
                font-size: {Typography.FONT_SIZE_BODY}pt;
                font-weight: {Typography.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            QPushButton:disabled {{
                background-color: {border_color};
                color: #999999;
            }}
            QPushButton:focus {{
                border: 2px solid {EnterpriseStyles._lighten(primary_color, 0.5)};
                outline: none;
            }}
        """
    
    @staticmethod
    def get_input_styles(bg_color: str, fg_color: str, border_color: str, 
                         focus_color: str) -> str:
        """Get input field styles."""
        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {bg_color};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                padding: {Spacing.SPACING_XS}px {Spacing.SPACING_SM}px;
                font-family: {Typography.FONT_FAMILY_PRIMARY};
                font-size: {Typography.FONT_SIZE_BODY}pt;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {focus_color};
            }}
            QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {{
                background-color: {border_color};
                color: #999999;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {fg_color};
            }}
        """
    
    @staticmethod
    def get_table_styles(bg_color: str, alt_bg: str, grid_color: str, 
                         header_bg: str, header_fg: str, primary_color: str = "#89b4fa") -> str:
        """Get table styles."""
        sel_hover = EnterpriseStyles._lighten(primary_color, 0.3)
        sel_pressed = EnterpriseStyles._darken(primary_color, 0.1)
        return f"""
            QTableWidget, QTableView {{
                background-color: {bg_color};
                alternate-background-color: {alt_bg};
                gridline-color: {grid_color};
                border: 1px solid {grid_color};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                font-family: {Typography.FONT_FAMILY_PRIMARY};
                font-size: {Typography.FONT_SIZE_BODY}pt;
            }}
            QTableWidget::item, QTableView::item {{
                padding: {Spacing.SPACING_SM}px;
                border: none;
                border-bottom: 1px solid {grid_color};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {primary_color};
                color: white;
            }}
            QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{
                background-color: {EnterpriseStyles._lighten(bg_color, 0.1)};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_fg};
                padding: {Spacing.SPACING_SM}px;
                border: none;
                border-bottom: 2px solid {grid_color};
                font-weight: {Typography.FONT_WEIGHT_SEMIBOLD};
                font-size: {Typography.FONT_SIZE_BODY}pt;
            }}
            QHeaderView::section:hover {{
                background-color: {sel_hover};
            }}
            QHeaderView::section:pressed {{
                background-color: {sel_pressed};
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: {header_bg};
                border: none;
            }}
        """
    
    @staticmethod
    def get_dialog_styles(bg_color: str, fg_color: str, border_color: str) -> str:
        """Get dialog styles."""
        return f"""
            QDialog {{
                background-color: {bg_color};
                color: {fg_color};
            }}
            QLabel {{
                color: {fg_color};
                font-family: {Typography.FONT_FAMILY_PRIMARY};
                font-size: {Typography.FONT_SIZE_BODY}pt;
            }}
        """
    
    @staticmethod
    def get_menu_styles(bg_color: str, fg_color: str, border_color: str, 
                       highlight_color: str) -> str:
        """Get menu styles."""
        return f"""
            QMenuBar {{
                background-color: {bg_color};
                color: {fg_color};
                border-bottom: 1px solid {border_color};
            }}
            QMenuBar::item {{
                padding: {Spacing.SPACING_XS}px {Spacing.SPACING_SM}px;
            }}
            QMenuBar::item:selected {{
                background-color: {highlight_color};
            }}
            QMenu {{
                background-color: {bg_color};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
            }}
            QMenu::item {{
                padding: {Spacing.SPACING_XS}px {Spacing.SPACING_LG}px;
            }}
            QMenu::item:selected {{
                background-color: {highlight_color};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {border_color};
                margin: {Spacing.SPACING_XS}px 0;
            }}
        """
    
    @staticmethod
    def get_scrollbar_styles(bg_color: str, handle_color: str) -> str:
        """Get scrollbar styles."""
        return f"""
            QScrollBar:vertical {{
                background-color: {bg_color};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {handle_color};
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #FF6B35;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {bg_color};
                height: 12px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {handle_color};
                min-width: 30px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: #FF6B35;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """


class StyleSheetBuilder:
    """Build complete stylesheets from components."""
    
    def __init__(self, theme: Dict):
        self._theme = theme
        
    def build_complete_stylesheet(self) -> str:
        """Build complete enterprise stylesheet."""
        bg = self._theme["background"].name()
        fg = self._theme["foreground"].name()
        primary = self._theme["primary"].name()
        secondary = self._theme["secondary"].name()
        input_bg = self._theme["input_background"].name()
        input_fg = self._theme["input_foreground"].name()
        border = self._theme["border"].name()
        
        styles = f"""
            /* Global styles */
            QWidget {{
                background-color: {bg};
                color: {fg};
                font-family: {Typography.FONT_FAMILY_PRIMARY};
                font-size: {Typography.FONT_SIZE_BODY}pt;
            }}
            
            /* Buttons */
            {EnterpriseStyles.get_button_styles(primary, bg, fg, border, input_bg)}
            
            /* Inputs */
            {EnterpriseStyles.get_input_styles(input_bg, input_fg, border, primary)}
            
            /* Tables */
            {EnterpriseStyles.get_table_styles(bg, input_bg, border, secondary, "white")}
            
            /* Menus */
            {EnterpriseStyles.get_menu_styles(bg, fg, border, primary)}
            
            /* Scrollbars */
            {EnterpriseStyles.get_scrollbar_styles(bg, border)}
            
            /* Labels */
            QLabel {{
                color: {fg};
            }}
            QLabel[heading="true"] {{
                font-size: {Typography.FONT_SIZE_H3}pt;
                font-weight: {Typography.FONT_WEIGHT_BOLD};
            }}
            
            /* Group Box */
            QGroupBox {{
                border: 1px solid {border};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                margin-top: {Spacing.SPACING_LG}px;
                padding-top: {Spacing.SPACING_MD}px;
                font-weight: {Typography.FONT_WEIGHT_SEMIBOLD};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {Spacing.SPACING_XS}px;
            }}
            
            /* Progress Bar */
            QProgressBar {{
                border: 1px solid {border};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                text-align: center;
                background-color: {input_bg};
            }}
            QProgressBar::chunk {{
                background-color: {primary};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
            }}
            
            /* Slider */
            QSlider::groove:horizontal {{
                border: 1px solid {border};
                height: 6px;
                background: {input_bg};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {primary};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            
            /* Tooltip */
            QToolTip {{
                background-color: {secondary};
                color: white;
                border: none;
                padding: {Spacing.SPACING_XS}px;
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
            }}
            
            /* Status Bar */
            QStatusBar {{
                background-color: {input_bg};
                border-top: 1px solid {border};
            }}
            
            /* Tab Widget */
            QTabWidget::pane {{
                border: 1px solid {border};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
                background-color: {bg};
            }}
            QTabBar::tab {{
                background-color: {input_bg};
                color: {fg};
                padding: {Spacing.SPACING_SM}px {Spacing.SPACING_MD}px;
                border-top-left-radius: {Spacing.BORDER_RADIUS_MD}px;
                border-top-right-radius: {Spacing.BORDER_RADIUS_MD}px;
            }}
            QTabBar::tab:selected {{
                background-color: {primary};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {border};
            }}
            
            /* List Widget */
            QListWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
            }}
            QListWidget::item {{
                padding: {Spacing.SPACING_SM}px;
            }}
            QListWidget::item:selected {{
                background-color: {primary};
                color: white;
            }}
        """
        return styles


# Singleton instance for global access
_global_style_builder: Optional[StyleSheetBuilder] = None

def get_style_builder(theme: Dict) -> StyleSheetBuilder:
    """Get global style builder instance."""
    global _global_style_builder
    if _global_style_builder is None or _global_style_builder._theme != theme:
        _global_style_builder = StyleSheetBuilder(theme)
    return _global_style_builder
with open('ui/finance/budgeting_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace imports
old_imports = '''"""Budgeting management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                  QLabel,
                                  QComboBox, QGroupBox, QTabWidget, QFrame,
                                  QWidget, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_DANGER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.tables import EnterpriseTable, TableColumn, build_table_stylesheet
from ui.components.state_helper import StateHelper

class BudgetingScreen(BaseScreen):'''

new_imports = '''"""Budgeting management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QGroupBox, QTabWidget, QFrame,
                                QWidget, QTableWidget, QTableWidgetItem,
                                QLineEdit, QDoubleSpinBox, QDateEdit, QMessageBox,
                                QTextEdit, QFormLayout, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt, QDate
from api.endpoints import get_endpoint
from api.client import APIClient
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_BODY,
                           BUTTON_HEIGHT_MD, TABLE_ROW_HEIGHT_MD, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_DANGER, INPUT_HEIGHT_MD, TEXT_CARD_TITLE, SPACING_XS, SPACING_XXL, COLOR_SUCCESS)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, ConfirmDialog
from ui.components.tables import EnterpriseTable, TableColumn, build_table_stylesheet
from ui.components.state_helper import StateHelper
from ui.components.forms import FormSection
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog, ConfirmDialog
from api.client import APIClient
from api.endpoints import get_endpoint

class BudgetingScreen(BaseScreen):'''

content = content.replace(old_imports, new_imports)

with open('ui/finance/budgeting_screen.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Imports updated')
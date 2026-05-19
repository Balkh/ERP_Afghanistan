"""
Phase 16 — Approved UI Primitives Registry.
Single source of truth for all approved enterprise UI components.
No unregistered component may be used in production screens.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ComponentCategory(Enum):
    BUTTON = auto()
    DIALOG = auto()
    FORM = auto()
    TABLE = auto()
    STATE = auto()
    TOAST = auto()
    TOOLBAR = auto()
    CARD = auto()
    INPUT = auto()
    LAYOUT = auto()
    NAVIGATION = auto()
    HEADER = auto()
    SPINNER = auto()
    BADGE = auto()


@dataclass(frozen=True)
class Primitive:
    name: str
    category: ComponentCategory
    module_path: str
    description: str
    forbidden_alternatives: List[str] = field(default_factory=list)
    governance_rules: List[str] = field(default_factory=list)


REGISTRY: Dict[str, Primitive] = {
    # ── BUTTONS ──
    "EnterpriseButton": Primitive(
        name="EnterpriseButton",
        category=ComponentCategory.BUTTON,
        module_path="ui.components.buttons",
        description="Single approved button primitive across all screens. Supports PRIMARY, SECONDARY, SUCCESS, DANGER, WARNING, GHOST variants.",
        forbidden_alternatives=["QPushButton", "QToolButton", "QCommandLinkButton", "QDialogButtonBox"],
        governance_rules=[
            "Must use ButtonVariant enum — never inline styles",
            "Must use ButtonSize enum — never fixedHeight/setMinimumHeight",
            "set_loading() for busy states — never custom disabled logic",
            "Focus ring via COLOR_FOCUS_RING token — never custom border"
        ]
    ),
    "IconButton": Primitive(
        name="IconButton",
        category=ComponentCategory.BUTTON,
        module_path="ui.components.buttons",
        description="Icon-only toolbar button. Extends EnterpriseButton, same governance.",
        forbidden_alternatives=["QPushButton with icon only", "QToolButton"],
        governance_rules=["Same as EnterpriseButton", "Square aspect ratio enforced"]
    ),
    "SplitButton": Primitive(
        name="SplitButton",
        category=ComponentCategory.BUTTON,
        module_path="ui.components.buttons",
        description="Split button with dropdown menu. Use for multi-action controls.",
        forbidden_alternatives=["QPushButton with custom menu"],
    ),

    # ── DIALOGS ──
    "EnterpriseDialog": Primitive(
        name="EnterpriseDialog",
        category=ComponentCategory.DIALOG,
        module_path="ui.components.dialogs",
        description="Standard enterprise dialog. Width-governed (min 400px, max 720px). Header/footer/body pattern.",
        forbidden_alternatives=["QDialog with custom layout", "QMessageBox for workflows"],
        governance_rules=[
            "Width must use DIALOG_WIDTH_FORM_MIN / DIALOG_WIDTH_FORM_PREFERRED",
            "Header font: TEXT_CARD_TITLE (16pt), not larger",
            "Footer separator: COLOR_FORM_FOOTER_BORDER",
            "Buttons: EnterpriseButton, never raw QPushButton"
        ]
    ),
    "ConfirmDialog": Primitive(
        name="ConfirmDialog",
        category=ComponentCategory.DIALOG,
        module_path="ui.components.dialogs",
        description="Confirmation dialog with EnterpriseButton actions.",
        forbidden_alternatives=["QMessageBox.question"],
    ),
    "InputDialog": Primitive(
        name="InputDialog",
        category=ComponentCategory.DIALOG,
        module_path="ui.components.dialogs",
        description="Input dialog with governed form layout.",
        forbidden_alternatives=["QInputDialog"],
    ),

    # ── FORMS ──
    "FormSection": Primitive(
        name="FormSection",
        category=ComponentCategory.FORM,
        module_path="ui.components.forms",
        description="Single approved form section layout. Supports single-column and 2-column grid modes with primary/secondary hierarchy.",
        forbidden_alternatives=["QGroupBox with custom layout", "QFormLayout standalone"],
        governance_rules=[
            "Must use primary=True for identity/critical sections, primary=False for secondary",
            "add_field_pair() for 2-column rows, add_full_width() for spanning",
            "Labels use _make_label() — never custom label styling",
            "Helper text via helper1/helper2/helper params — never inline labels"
        ]
    ),
    "FormField": Primitive(
        name="FormField",
        category=ComponentCategory.FORM,
        module_path="ui.components.forms",
        description="Individual form field with label, input, helper text, and inline validation.",
        forbidden_alternatives=["QLabel + QLineEdit custom pairing"],
        governance_rules=[
            "helper_text for contextual hints — never tooltip-only",
            "set_error() triggers inline validation UX",
            "Uses FieldType enum for input type selection"
        ]
    ),
    "EnterpriseForm": Primitive(
        name="EnterpriseForm",
        category=ComponentCategory.FORM,
        module_path="ui.components.forms",
        description="Full enterprise form with scroll, validation, and action buttons.",
        forbidden_alternatives=["QScrollArea + custom form layout"],
    ),

    # ── TABLES ──
    "EnterpriseTable": Primitive(
        name="EnterpriseTable",
        category=ComponentCategory.TABLE,
        module_path="ui.components.tables",
        description="Single approved data table. Supports density tiers: compact/medium/relaxed.",
        forbidden_alternatives=["QTableWidget standalone", "QTreeWidget for tabular data"],
        governance_rules=[
            "Must use TableColumn definitions — never raw column setup",
            "Must use build_table_stylesheet() — never inline table stylesheets",
            "Density via set_density('compact'|'medium'|'relaxed') — never setDefaultSectionSize",
            "Selection via TableSelectionMode enum",
            "load_state() / save_state() for column persistence"
        ]
    ),
    "DataEntryGrid": Primitive(
        name="DataEntryGrid",
        category=ComponentCategory.TABLE,
        module_path="ui.components.tables",
        description="Editable grid for interactive line-item entry.",
        forbidden_alternatives=["QTableWidget with custom delegate"],
    ),
    "PaginationWidget": Primitive(
        name="PaginationWidget",
        category=ComponentCategory.TABLE,
        module_path="ui.components.tables",
        description="Standard pagination bar.",
        forbidden_alternatives=["Custom page navigation"],
    ),

    # ── STATE ──
    "StateHelper": Primitive(
        name="StateHelper",
        category=ComponentCategory.STATE,
        module_path="ui.components.state_helper",
        description="Loading, empty, and error state manager. No emoji — geometric indicators only.",
        forbidden_alternatives=["Custom QLabel for states", "QStackedWidget manual state"],
        governance_rules=[
            "show_empty() with actions param — never static empty labels",
            "show_error() with on_retry and actions — never QMessageBox for errors",
            "Geometric indicator bars only — no emoji, icons, clipart"
        ]
    ),

    # ── TOAST ──
    "NotificationManager": Primitive(
        name="NotificationManager",
        category=ComponentCategory.TOAST,
        module_path="ui.components.notifications",
        description=(
            "Unified notification system (title+message and simple message modes). "
            "Single instance via get_notification_manager()."
        ),
        forbidden_alternatives=["QMessageBox for success/error", "QStatusBar for notifications", "QPushButton close buttons"],
        governance_rules=[
            "show_success / show_error / show_warning / show_info for simple messages",
            "notify_success / notify_error / notify_warning / notify_info for title+message",
            "Adaptive text contrast via COLOR_TEXT_ON_SUCCESS / COLOR_TEXT_ON_DANGER / etc.",
            "Workflow reassurance messages via WORKFLOW_SAVED / WORKFLOW_UPDATED / etc.",
            "Close button must use IconButton (not raw QPushButton)",
            "Keyboard dismiss via Escape key"
        ]
    ),
    # ── CARDS ──
    "KPICard": Primitive(
        name="KPICard",
        category=ComponentCategory.CARD,
        module_path="ui.components.kpi_cards",
        description="Primary KPI metric card for dashboards and financial summaries.",
        forbidden_alternatives=["QFrame with custom layout for metrics"],
    ),
    "MiniMetricCard": Primitive(
        name="MiniMetricCard",
        category=ComponentCategory.CARD,
        module_path="ui.components.kpi_cards",
        description="Secondary/diagnostic metric card for role-specific sections.",
    ),
    "StatusBadge": Primitive(
        name="StatusBadge",
        category=ComponentCategory.CARD,
        module_path="ui.components.kpi_cards",
        description="Compact status indicator for alert rows and inline status.",
    ),

    # ── NAVIGATION ──
    "Sidebar": Primitive(
        name="Sidebar",
        category=ComponentCategory.NAVIGATION,
        module_path="ui.sidebar",
        description="Application sidebar navigation. Single instance with collapsible groups.",
        forbidden_alternatives=["QListWidget navigation", "Custom QWidget sidebar"],
        governance_rules=[
            "set_active_item() for active state — never manual button styling",
            "Navigation items via page_id system — never dynamic addWidget"
        ]
    ),
    "NavigationHeader": Primitive(
        name="NavigationHeader",
        category=ComponentCategory.HEADER,
        module_path="ui.components.navigation_header",
        description="Standard navigation header with breadcrumb, back/home/close.",
        forbidden_alternatives=["Custom header layout per screen"],
    ),

    # ── SPINNER ──
    "LoadingSpinner": Primitive(
        name="LoadingSpinner",
        category=ComponentCategory.SPINNER,
        module_path="ui.components.loading_spinner",
        description="Circular loading spinner with QPainter arc rendering.",
        forbidden_alternatives=["QMovie GIF spinner", "QLabel with animated text"],
    ),

    # ── BADGE ──
    "BadgeRenderer": Primitive(
        name="BadgeRenderer",
        category=ComponentCategory.BADGE,
        module_path="ui.rendering.badge_renderer",
        description="Status badge rendering (this is an exception — kept for backward compatibility only).",
        governance_rules=["DEPRECATED — do not use in new screens"],
    ),
}


def is_approved(component_name: str) -> bool:
    return component_name in REGISTRY


def get_primitive(component_name: str) -> Optional[Primitive]:
    return REGISTRY.get(component_name)


def find_forbidden_usage(component_name: str) -> List[str]:
    for name, prim in REGISTRY.items():
        if component_name in prim.forbidden_alternatives:
            return [name]
    return []


def get_by_category(category: ComponentCategory) -> List[Primitive]:
    return [p for p in REGISTRY.values() if p.category == category]

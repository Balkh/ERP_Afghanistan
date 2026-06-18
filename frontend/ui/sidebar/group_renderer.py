"""
Sidebar group rendering and toggle logic.

Handles creating collapsible group widgets and toggling their
expanded/collapsed state. Used by Sidebar.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QApplication
from PySide6.QtCore import Qt
from ui.components.buttons import EnterpriseButton
from ui.constants import (
    SPACING_NONE, SPACING_XS, SPACING_SM, SPACING_XL,
    COLOR_BG_MAIN,
)
from ui.sidebar.sidebar_styles import group_header_style


def create_group(parent_layout, title, group_name, items, expanded_groups,
                 group_widgets, navigation_items, create_nav_button_fn, sidebar):
    """Create a collapsible group with header and item buttons.

    Args:
        parent_layout: QVBoxLayout to add the group to.
        title: Display title for the group header.
        group_name: Internal key (e.g. "inventory").
        items: List of (title, page_id, page_index) tuples.
        expanded_groups: dict tracking expansion state.
        group_widgets: dict to store the group widget reference.
        navigation_items: dict to store page_id → button references.
        create_nav_button_fn: callable(title, page_id, page_index) → EnterpriseButton.
        sidebar: Sidebar instance (for signal connections).
    """
    group_widget = QWidget()
    group_widget.setStyleSheet("background-color: transparent;")
    group_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    group_layout = QVBoxLayout(group_widget)
    group_layout.setContentsMargins(0, 0, 0, 0)
    group_layout.setSpacing(SPACING_NONE)

    is_expanded = expanded_groups.get(group_name, False)
    arrow = "▼" if is_expanded else "▶"
    header_btn = EnterpriseButton(f"{arrow}  {title}")
    header_btn.setCursor(Qt.PointingHandCursor)
    header_btn.setFixedHeight(42)
    header_btn.setStyleSheet(group_header_style())
    header_btn.setProperty("group_name", group_name)
    header_btn.clicked.connect(lambda checked, g=group_name: sidebar._toggle_group(g))

    group_layout.addWidget(header_btn)
    setattr(sidebar, f"_{group_name}_header", header_btn)

    items_widget = QWidget()
    items_widget.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
    items_layout = QVBoxLayout(items_widget)
    items_layout.setContentsMargins(SPACING_XL + SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
    items_layout.setSpacing(SPACING_XS)

    for item_title, page_id, page_index in items:
        btn = create_nav_button_fn(item_title, page_id, page_index)
        items_layout.addWidget(btn)

    group_layout.addWidget(items_widget)
    group_widgets[group_name] = group_widget
    parent_layout.addWidget(group_widget)

    if not is_expanded:
        items_widget.setVisible(False)
        items_widget.setMaximumHeight(0)
        group_widget.setMaximumHeight(42)
    else:
        items_widget.setVisible(True)
        items_widget.setMaximumHeight(16777215)
        group_widget.setMaximumHeight(16777215)


def toggle_group(group_name, expanded_groups, group_widgets, sidebar):
    """Toggle a group's expanded/collapsed state.

    Args:
        group_name: Internal key for the group.
        expanded_groups: dict tracking expansion state (mutated in place).
        group_widgets: dict of group_name → group QWidget.
        sidebar: Sidebar instance (for header attribute lookup).

    Returns:
        None
    """
    current_state = expanded_groups.get(group_name, False)
    new_state = not current_state
    expanded_groups[group_name] = new_state

    group_widget = group_widgets.get(group_name)
    if not group_widget:
        return

    header_btn = getattr(sidebar, f"_{group_name}_header", None)

    # Find items_widget (the second widget in the group layout)
    items_widget = None
    layout = group_widget.layout()
    for i in range(layout.count()):
        widget = layout.itemAt(i).widget()
        if widget and widget != header_btn:
            items_widget = widget
            break

    # Get the title text from the button (strip arrow prefix)
    title_text = ""
    if header_btn:
        btn_text = header_btn.text()
        title_text = btn_text.replace("▶ ", "").replace("▼ ", "")

    if new_state:
        if items_widget:
            items_widget.setVisible(True)
            items_widget.setMaximumHeight(16777215)
        if header_btn:
            header_btn.setText(f"▼  {title_text}")
        group_widget.setMaximumHeight(16777215)
    else:
        if items_widget:
            items_widget.setVisible(False)
            items_widget.setMaximumHeight(0)
        if header_btn:
            header_btn.setText(f"▶  {title_text}")
        group_widget.setMaximumHeight(42)

    group_widget.layout().invalidate()
    group_widget.update()

    QApplication.processEvents()

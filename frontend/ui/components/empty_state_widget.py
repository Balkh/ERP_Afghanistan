"""Enterprise empty state widget — replaces raw QLabel("No data") / QLabel("Loading...") patterns."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.constants import (
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    BORDER_RADIUS_LG,
    COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    TEXT_CARD_TITLE, TEXT_BODY, TEXT_LABEL,
    FONT_NAME_PRIMARY,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


class EmptyStateWidget(QFrame):
    def __init__(
        self,
        icon_text: str = "",
        title: str = "No data",
        description: str = "",
        action_text: str = "",
        action_callback=None,
        parent=None,
    ):
        super().__init__(parent)

        self._action_callback = action_callback

        self.setObjectName("EmptyStateWidget")
        self.setMinimumHeight(300)
        self.setMaximumWidth(500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setStyleSheet(
            f"#EmptyStateWidget {{"
            f"  background-color: {COLOR_BG_ELEVATED};"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  border-radius: {BORDER_RADIUS_LG}px;"
            f"}}"
        )

        self._build_ui(icon_text, title, description, action_text)

    def _build_ui(self, icon_text: str, title: str, description: str, action_text: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACING_LG)
        layout.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_XL)

        if icon_text:
            icon_label = QLabel(icon_text)
            font = QFont(FONT_NAME_PRIMARY, 48)
            icon_label.setFont(font)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_font = QFont(FONT_NAME_PRIMARY, TEXT_CARD_TITLE)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: transparent;")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_font = QFont(FONT_NAME_PRIMARY, TEXT_BODY)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            layout.addWidget(desc_label)

        if action_text:
            self._action_button = EnterpriseButton(
                text=action_text,
                variant=ButtonVariant.PRIMARY,
                size=ButtonSize.MEDIUM,
                parent=self,
            )
            self._action_button.clicked.connect(self._on_action_clicked)
            btn_layout = QVBoxLayout()
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(self._action_button)
            layout.addLayout(btn_layout)

    def _on_action_clicked(self):
        if self._action_callback:
            self._action_callback()

    def set_action_callback(self, callback) -> None:
        self._action_callback = callback

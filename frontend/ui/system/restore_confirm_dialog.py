"""Pre-restore confirmation dialog with metadata summary."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFrame
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD,
                           MARGIN_CARD, COLOR_BG_MAIN, COLOR_FORM_FOOTER_BORDER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType


class RestoreConfirmDialog(EnterpriseDialog):
    """Pre-restore confirmation dialog with metadata summary."""

    def __init__(self, metadata: dict, parent=None):
        super().__init__("Confirm Restore", DialogType.CUSTOM, parent)
        content = self._build_content(metadata)
        self.set_content(content)

    def _build_content(self, metadata: dict) -> QWidget:
        from theme.style_builder import UIStyleBuilder

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(SPACING_MD)

        warning = QLabel(
            "! This will replace the current database with the selected backup. "
            "An emergency backup will be created automatically before restore."
        )
        warning.setStyleSheet(UIStyleBuilder.get_label_style("warning"))
        warning.setWordWrap(True)
        layout.addWidget(warning)

        info_group = QGroupBox("Backup Metadata")
        info_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        info_layout = QVBoxLayout()
        info_layout.setSpacing(SPACING_XS)

        fields = [
            ("Filename", metadata.get('filename', 'N/A')),
            ("Size", metadata.get('size_mb', metadata.get('size', 'N/A'))),
            ("Created", metadata.get('created_at', metadata.get('timestamp', 'N/A'))),
            ("Encrypted", "Yes" if metadata.get('encrypted', False) else "No"),
            ("Checksum", (str(metadata.get('checksum', 'N/A'))[:32] + '...') if len(str(metadata.get('checksum', 'N/A'))) > 32 else str(metadata.get('checksum', 'N/A'))),
        ]
        for label, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(UIStyleBuilder.get_label_style("label"))
            row.addWidget(lbl)
            row.addStretch()
            val = QLabel(str(value))
            val.setStyleSheet(UIStyleBuilder.get_label_style("body"))
            row.addWidget(val)
            info_layout.addLayout(row)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        return widget

    def _create_button_area(self):
        button_area = QFrame()
        button_area.setFixedHeight(60)

        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(MARGIN_CARD, SPACING_SM, MARGIN_CARD, SPACING_SM)

        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        layout.addStretch()

        confirm_btn = EnterpriseButton(text="Confirm Restore", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        confirm_btn.clicked.connect(self.accept)
        layout.addWidget(confirm_btn)

        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
                border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
            }}
        """)
        return button_area

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui.constants import TEXT_PAGE_TITLE, COLOR_TEXT_PRIMARY


class ControlCenterScreen(QWidget):
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self._api_client = api_client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Control Center")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)
        info = QLabel("Control Center is available via the backend API at /api/control-center/.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(info)
        layout.addStretch()

    def _on_screen_shown(self):
        pass

    def _on_screen_hidden(self):
        pass

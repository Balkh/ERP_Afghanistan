from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from ui.constants import (
    COLOR_TABLE_HEADER, COLOR_TABLE_ALT, COLOR_TABLE_GRIDLINE,
    COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, COLOR_BORDER,
    COLOR_PRIMARY, COLOR_BORDER_LIGHT, COLOR_BG_ELEVATED,
    TEXT_TABLE, TEXT_TABLE_HEADER, TABLE_ROW_HEIGHT_MD, SPACING_6)


class TableRenderer:
    @staticmethod
    def style(table: QTableWidget, alt_rows: bool = True) -> None:
        table.setAlternatingRowColors(alt_rows)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLOR_BG_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                gridline-color: {COLOR_TABLE_GRIDLINE};
                font-size: {TEXT_TABLE}px;
            }}
            QTableWidget::item {{
                padding: {SPACING_6}px 8px;
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY};
                color: white;
            }}
            QTableWidget::item:hover:!selected {{
                background-color: {COLOR_BG_ELEVATED};
            }}
            QHeaderView::section {{
                background-color: {COLOR_TABLE_HEADER};
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_6}px 8px;
                border: none;
                font-weight: bold;
                font-size: {TEXT_TABLE_HEADER}px;
            }}
        """)
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)

"""
Legacy TableRenderer — delegates to canonical EnterpriseTable styling.
No longer contains hardcoded colors or QSS. All styling comes from
ui/components/tables.py:build_table_stylesheet().
"""

from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from ui.components.tables import build_table_stylesheet
from ui.constants import TABLE_ROW_HEIGHT_MD, SPACING_6


class TableRenderer:
    @staticmethod
    def style(table: QTableWidget, alt_rows: bool = True) -> None:
        table.setAlternatingRowColors(alt_rows)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setStyleSheet(build_table_stylesheet())
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_MD)

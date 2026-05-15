from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor


def diff_update_table(table, rows, col_count=None):
    scroll_bar = table.verticalScrollBar()
    scroll_pos = scroll_bar.value() if scroll_bar else 0
    sel_row = table.currentRow()
    sel_col = table.currentColumn()

    if col_count is None and rows:
        col_count = max(len(r) for r in rows) if isinstance(rows[0], (list, tuple)) else table.columnCount()
    elif col_count is None:
        col_count = table.columnCount()

    table.setUpdatesEnabled(False)
    old_count = table.rowCount()
    new_count = len(rows)

    if new_count != old_count:
        table.setRowCount(new_count)

    for i, row in enumerate(rows):
        for j in range(col_count):
            val = row[j] if j < len(row) else ""
            if isinstance(val, QTableWidgetItem):
                text = val.text()
                fg = val.foreground()
            else:
                text = str(val)
                fg = None
            item = table.item(i, j)
            if item is None:
                if isinstance(val, QTableWidgetItem):
                    new_item = QTableWidgetItem()
                    new_item.setText(val.text())
                    new_item.setForeground(val.foreground())
                    table.setItem(i, j, new_item)
                else:
                    table.setItem(i, j, QTableWidgetItem(text))
            elif item.text() != text:
                item.setText(text)
                if fg is not None and fg != item.foreground():
                    item.setForeground(fg)

    table.setUpdatesEnabled(True)
    if scroll_bar and scroll_pos > 0:
        scroll_bar.setValue(min(scroll_pos, scroll_bar.maximum()))
    if 0 <= sel_row < new_count:
        table.setCurrentCell(sel_row, max(0, sel_col))

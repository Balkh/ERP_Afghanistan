"""Unit tests for export_payroll_to_excel standalone function.

Tests the Excel export logic with mocked openpyxl, QFileDialog, and AlertDialog.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_table():
    """Create a mock EnterpriseTable with sample payroll data."""
    table = MagicMock()
    table.get_row_data.return_value = [
        {
            "employee_name": "Ahmad Rostami",
            "period": "April 2026",
            "basic_salary": "15000.00",
            "total_allowances": "2500.00",
            "total_deductions": "1800.00",
            "gross_salary": "17500.00",
            "net_salary": "15700.00",
            "status": "Paid",
        },
        {
            "employee_name": "Maria Haq",
            "period": "April 2026",
            "basic_salary": "20000.00",
            "total_allowances": "3000.00",
            "total_deductions": "2500.00",
            "gross_salary": "23000.00",
            "net_salary": "20500.00",
            "status": "Paid",
        },
    ]
    return table


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_successful_export(mock_wb_cls, mockFileDialog, mockAlert, mock_table):
    """Successful export writes Excel file and shows success dialog."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = f.name
    try:
        mockFileDialog.getSaveFileName.return_value = (temp_path, "")
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_wb_cls.return_value = mock_wb

        from ui.hr.payroll_dialogs import export_payroll_to_excel
        export_payroll_to_excel(mock_table, parent=None)

        mock_wb.save.assert_called_once_with(temp_path)
        mockAlert.info.assert_called_once()
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_cancelled_export(mock_wb_cls, mockFileDialog, mockAlert, mock_table):
    """User cancelling the file dialog shows cancelled warning."""
    mockFileDialog.getSaveFileName.return_value = ("", "")

    from ui.hr.payroll_dialogs import export_payroll_to_excel
    export_payroll_to_excel(mock_table, parent=None)

    mockAlert.warning.assert_called_once()
    assert "cancelled" in mockAlert.warning.call_args[0][1].lower()


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_empty_records(mock_wb_cls, mockFileDialog, mockAlert):
    """Empty records table still produces a valid export."""
    table = MagicMock()
    table.get_row_data.return_value = []

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = f.name
    try:
        mockFileDialog.getSaveFileName.return_value = (temp_path, "")
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_wb_cls.return_value = mock_wb

        from ui.hr.payroll_dialogs import export_payroll_to_excel
        export_payroll_to_excel(table, parent=None)

        mock_wb.save.assert_called_once_with(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_excel_headers_written(mock_wb_cls, mockFileDialog, mockAlert, mock_table):
    """Export should write correct column headers."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = f.name
    try:
        mockFileDialog.getSaveFileName.return_value = (temp_path, "")
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_wb_cls.return_value = mock_wb

        from ui.hr.payroll_dialogs import export_payroll_to_excel
        export_payroll_to_excel(mock_table, parent=None)

        expected_headers = [
            "Employee", "Period", "Basic Salary", "Allowances",
            "Deductions", "Gross", "Net", "Status",
        ]
        header_calls = [
            call for call in mock_ws.cell.call_args_list
            if call[1].get("row") == 1
        ]
        assert len(header_calls) == 8
        actual_headers = [call[1]["value"] for call in header_calls]
        assert actual_headers == expected_headers
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_data_rows_written(mock_wb_cls, mockFileDialog, mockAlert, mock_table):
    """Export should write data rows for each record."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = f.name
    try:
        mockFileDialog.getSaveFileName.return_value = (temp_path, "")
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_wb_cls.return_value = mock_wb

        from ui.hr.payroll_dialogs import export_payroll_to_excel
        export_payroll_to_excel(mock_table, parent=None)

        # 2 records × 8 columns = 16 data cell calls (row >= 2)
        data_calls = [
            call for call in mock_ws.cell.call_args_list
            if call[1].get("row", 0) >= 2
        ]
        assert len(data_calls) == 16
        # First data row should have Ahmad's data
        first_row_calls = [c for c in data_calls if c[1]["row"] == 2]
        assert first_row_calls[0][1]["value"] == "Ahmad Rostami"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@patch("ui.hr.payroll_dialogs.AlertDialog")
@patch("ui.hr.payroll_dialogs.QFileDialog")
@patch("openpyxl.Workbook")
def test_exception_shows_error_dialog(mock_wb_cls, mockFileDialog, mockAlert, mock_table):
    """Exception during export shows error dialog."""
    mockFileDialog.getSaveFileName.side_effect = RuntimeError("disk full")

    from ui.hr.payroll_dialogs import export_payroll_to_excel
    export_payroll_to_excel(mock_table, parent=None)

    mockAlert.error.assert_called_once()
    assert "disk full" in mockAlert.error.call_args[0][1]

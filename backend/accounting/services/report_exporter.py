import csv
import io
import base64
from decimal import Decimal
from datetime import date
from typing import Optional


class ReportExporter:
    """
    Export financial reports to various formats.

    Supports: CSV, JSON-ready, and structured text (PDF-ready).
    """

    @staticmethod
    def generate_qr_code_base64(report_data: dict, report_type: str) -> str:
        """
        Generate a QR code for the report as base64 PNG.
        Embeds report metadata for verification.
        """
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr_data = f"REPORT={report_type}|DATE={date.today().isoformat()}"
            if 'as_of_date' in report_data:
                qr_data += f"|AS_OF={report_data['as_of_date']}"
            if 'start_date' in report_data and 'end_date' in report_data:
                qr_data += f"|FROM={report_data['start_date']}|TO={report_data['end_date']}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def to_csv(report_data: dict, report_type: str) -> str:
        """Export report data to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == 'trial_balance':
            ReportExporter._export_trial_balance_csv(writer, report_data)
        elif report_type == 'profit_loss':
            ReportExporter._export_profit_loss_csv(writer, report_data)
        elif report_type == 'balance_sheet':
            ReportExporter._export_balance_sheet_csv(writer, report_data)
        elif report_type == 'ledger':
            ReportExporter._export_ledger_csv(writer, report_data)
        elif report_type == 'cash_flow':
            ReportExporter._export_cash_flow_csv(writer, report_data)
        elif report_type == 'ar_aging':
            ReportExporter._export_ar_aging_csv(writer, report_data)
        elif report_type == 'ap_aging':
            ReportExporter._export_ap_aging_csv(writer, report_data)
        else:
            ReportExporter._export_generic_csv(writer, report_data)

        return output.getvalue()

    @staticmethod
    def to_text(report_data: dict, report_type: str, company_name: str = '') -> str:
        """Export report to formatted text (PDF-ready layout)."""
        lines = []
        lines.append('=' * 80)
        lines.append(f'{company_name or "Pharmacy ERP"}')
        lines.append(f'{report_data.get("report_type", "Report")}')
        if 'as_of_date' in report_data:
            lines.append(f'As of: {report_data["as_of_date"]}')
        if 'start_date' in report_data and 'end_date' in report_data:
            lines.append(f'Period: {report_data["start_date"]} to {report_data["end_date"]}')
        lines.append('-' * 80)

        if report_type == 'trial_balance':
            ReportExporter._format_trial_balance_text(lines, report_data)
        elif report_type == 'profit_loss':
            ReportExporter._format_profit_loss_text(lines, report_data)
        elif report_type == 'balance_sheet':
            ReportExporter._format_balance_sheet_text(lines, report_data)
        elif report_type == 'ledger':
            ReportExporter._format_ledger_text(lines, report_data)
        elif report_type == 'cash_flow':
            ReportExporter._format_cash_flow_text(lines, report_data)
        elif report_type == 'ar_aging':
            ReportExporter._format_ar_aging_text(lines, report_data)
        elif report_type == 'ap_aging':
            ReportExporter._format_ap_aging_text(lines, report_data)

        lines.append('-' * 80)
        lines.append(f'Generated: {date.today().isoformat()}')
        lines.append(f'Verify: Scan QR code on PDF/Print version')
        lines.append('=' * 80)

        return '\n'.join(lines)

    @staticmethod
    def _fmt(amount) -> str:
        """Format decimal amount."""
        if isinstance(amount, Decimal):
            return f'{amount:,.2f}'
        return f'{float(amount):,.2f}' if amount else '0.00'

    @staticmethod
    def _export_trial_balance_csv(writer, data):
        writer.writerow(['Account Code', 'Account Name', 'Type', 'Category', 'Debit', 'Credit', 'Net Balance', 'Balance Type'])
        for row in data.get('accounts', []):
            writer.writerow([
                row['account_code'], row['account_name'], row['account_type'],
                row.get('account_category', ''), ReportExporter._fmt(row['total_debit']),
                ReportExporter._fmt(row['total_credit']), ReportExporter._fmt(row['net_balance']),
                row['balance_type']
            ])
        writer.writerow([])
        writer.writerow(['', '', '', 'TOTALS', ReportExporter._fmt(data.get('total_debit', 0)),
                         ReportExporter._fmt(data.get('total_credit', 0)), '',
                         'Balanced' if data.get('is_balanced') else 'NOT BALANCED'])

    @staticmethod
    def _export_profit_loss_csv(writer, data):
        writer.writerow(['Category', 'Account Code', 'Account Name', 'Amount'])
        writer.writerow(['REVENUE'])
        for section in data.get('revenue', []):
            if isinstance(section, dict) and 'accounts' in section:
                writer.writerow([section.get('category', ''), '', '', ReportExporter._fmt(section.get('total', 0))])
                for acc in section.get('accounts', []):
                    writer.writerow(['', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
            else:
                writer.writerow(['', section.get('account_code', ''), section.get('account_name', ''), ReportExporter._fmt(section.get('amount', 0))])
        writer.writerow(['', '', 'Total Revenue', ReportExporter._fmt(data.get('total_revenue', 0))])
        writer.writerow(['COGS'])
        for section in data.get('cogs', []):
            if isinstance(section, dict) and 'accounts' in section:
                for acc in section.get('accounts', []):
                    writer.writerow(['', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
        writer.writerow(['', '', 'Total COGS', ReportExporter._fmt(data.get('total_cogs', 0))])
        writer.writerow(['', '', 'Gross Profit', ReportExporter._fmt(data.get('gross_profit', 0))])
        writer.writerow(['EXPENSES'])
        for section in data.get('expenses', []):
            if isinstance(section, dict) and 'accounts' in section:
                writer.writerow([section.get('category', ''), '', '', ReportExporter._fmt(section.get('total', 0))])
                for acc in section.get('accounts', []):
                    writer.writerow(['', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
            else:
                writer.writerow(['', section.get('account_code', ''), section.get('account_name', ''), ReportExporter._fmt(section.get('amount', 0))])
        writer.writerow(['', '', 'Total Expenses', ReportExporter._fmt(data.get('total_expenses', 0))])
        writer.writerow([])
        writer.writerow(['', '', 'NET INCOME', ReportExporter._fmt(data.get('net_income', 0))])

    @staticmethod
    def _export_balance_sheet_csv(writer, data):
        writer.writerow(['Section', 'Category', 'Account Code', 'Account Name', 'Amount'])
        for section in data.get('assets', {}).get('sections', []):
            writer.writerow(['ASSETS', section.get('category', ''), '', '', ReportExporter._fmt(section.get('total', 0))])
            for acc in section.get('accounts', []):
                writer.writerow(['', '', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
        writer.writerow(['', '', '', 'Total Assets', ReportExporter._fmt(data.get('assets', {}).get('total', 0))])

        for section in data.get('liabilities', {}).get('sections', []):
            writer.writerow(['LIABILITIES', section.get('category', ''), '', '', ReportExporter._fmt(section.get('total', 0))])
            for acc in section.get('accounts', []):
                writer.writerow(['', '', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
        writer.writerow(['', '', '', 'Total Liabilities', ReportExporter._fmt(data.get('liabilities', {}).get('total', 0))])

        for section in data.get('equity', {}).get('sections', []):
            writer.writerow(['EQUITY', section.get('category', ''), '', '', ReportExporter._fmt(section.get('total', 0))])
            for acc in section.get('accounts', []):
                writer.writerow(['', '', acc['account_code'], acc['account_name'], ReportExporter._fmt(acc['amount'])])
        writer.writerow(['', '', '', 'Total Equity', ReportExporter._fmt(data.get('equity', {}).get('total', 0))])

    @staticmethod
    def _export_ledger_csv(writer, data):
        writer.writerow(['Entry Number', 'Date', 'Type', 'Description', 'Reference', 'Debit', 'Credit', 'Running Balance'])
        for entry in data.get('entries', []):
            writer.writerow([
                entry['entry_number'], entry['entry_date'], entry['entry_type'],
                entry['description'], entry.get('reference', ''),
                ReportExporter._fmt(entry['debit']), ReportExporter._fmt(entry['credit']),
                ReportExporter._fmt(entry['running_balance'])
            ])

    @staticmethod
    def _export_cash_flow_csv(writer, data):
        writer.writerow(['Section', 'Description', 'Amount'])
        op = data.get('operating_activities', {})
        writer.writerow(['Operating Activities', 'Net Income', ReportExporter._fmt(op.get('net_income', 0))])
        for item in op.get('working_capital_changes', []):
            writer.writerow(['Operating Activities', item.get('description', ''), ReportExporter._fmt(item.get('change', 0))])
        writer.writerow(['', 'Net Cash from Operations', ReportExporter._fmt(op.get('net_cash_from_operations', 0))])

        inv = data.get('investing_activities', {})
        for item in inv.get('items', []):
            writer.writerow(['Investing Activities', item.get('description', ''), ReportExporter._fmt(item.get('change', 0))])
        writer.writerow(['', 'Net Cash from Investing', ReportExporter._fmt(inv.get('net_cash_from_investing', 0))])

        fin = data.get('financing_activities', {})
        for item in fin.get('items', []):
            writer.writerow(['Financing Activities', item.get('description', ''), ReportExporter._fmt(item.get('change', 0))])
        writer.writerow(['', 'Net Cash from Financing', ReportExporter._fmt(fin.get('net_cash_from_financing', 0))])
        writer.writerow([])
        writer.writerow(['', 'Net Change in Cash', ReportExporter._fmt(data.get('net_change_in_cash', 0))])
        writer.writerow(['', 'Opening Cash Balance', ReportExporter._fmt(data.get('opening_cash_balance', 0))])
        writer.writerow(['', 'Closing Cash Balance', ReportExporter._fmt(data.get('closing_cash_balance', 0))])

    @staticmethod
    def _export_ar_aging_csv(writer, data):
        writer.writerow(['Customer', 'Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days', 'Total Outstanding'])
        for row in data.get('aging_rows', []):
            writer.writerow([
                row.get('party_name', ''),
                ReportExporter._fmt(row.get('current', 0)),
                ReportExporter._fmt(row.get('age_1_30', 0)),
                ReportExporter._fmt(row.get('age_31_60', 0)),
                ReportExporter._fmt(row.get('age_61_90', 0)),
                ReportExporter._fmt(row.get('age_90_plus', 0)),
                ReportExporter._fmt(row.get('total', 0)),
            ])

    @staticmethod
    def _export_ap_aging_csv(writer, data):
        writer.writerow(['Supplier', 'Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days', 'Total Outstanding'])
        for row in data.get('aging_rows', []):
            writer.writerow([
                row.get('party_name', ''),
                ReportExporter._fmt(row.get('current', 0)),
                ReportExporter._fmt(row.get('age_1_30', 0)),
                ReportExporter._fmt(row.get('age_31_60', 0)),
                ReportExporter._fmt(row.get('age_61_90', 0)),
                ReportExporter._fmt(row.get('age_90_plus', 0)),
                ReportExporter._fmt(row.get('total', 0)),
            ])

    @staticmethod
    def _export_generic_csv(writer, data):
        for key, value in data.items():
            writer.writerow([key, value])

    # Text formatters
    @staticmethod
    def _format_trial_balance_text(lines, data):
        lines.append(f'{"Code":<12} {"Account Name":<35} {"Debit":>14} {"Credit":>14} {"Net":>14} {"Type":<7}')
        lines.append('-' * 100)
        for row in data.get('accounts', []):
            indent = '  ' * (row.get('level', 0) or 0)
            lines.append(f'{indent}{row["account_code"]:<12} {row["account_name"]:<35} {ReportExporter._fmt(row["total_debit"]):>14} {ReportExporter._fmt(row["total_credit"]):>14} {ReportExporter._fmt(row["net_balance"]):>14} {row["balance_type"]:<7}')
        lines.append('-' * 100)
        lines.append(f'{"TOTALS":<49} {ReportExporter._fmt(data.get("total_debit", 0)):>14} {ReportExporter._fmt(data.get("total_credit", 0)):>14}')
        lines.append(f'Difference: {ReportExporter._fmt(data.get("difference", 0))} | {"BALANCED" if data.get("is_balanced") else "NOT BALANCED"}')

    @staticmethod
    def _format_profit_loss_text(lines, data):
        lines.append(f'{"Description":<50} {"Amount":>14}')
        lines.append('-' * 66)

        def _write_section(title, items, total, is_subtract=False):
            lines.append(title)
            for item in items:
                if isinstance(item, dict) and 'accounts' in item:
                    lines.append(f'  {item.get("category", ""):<48} {ReportExporter._fmt(item.get("total", 0)):>14}')
                    for acc in item.get('accounts', []):
                        lines.append(f'    {acc["account_code"]} - {acc["account_name"]:<40} {ReportExporter._fmt(acc["amount"]):>14}')
                else:
                    lines.append(f'    {item.get("account_code", "")} - {item.get("account_name", ""):<40} {ReportExporter._fmt(item.get("amount", 0)):>14}')
            lines.append(f'  {"Total " + title:<48} {ReportExporter._fmt(total):>14}')
            lines.append('')

        _write_section('Revenue', data.get('revenue', []), data.get('total_revenue', 0))
        _write_section('COGS', data.get('cogs', []), data.get('total_cogs', 0))
        lines.append(f'{"Gross Profit":<50} {ReportExporter._fmt(data.get("gross_profit", 0)):>14}')
        lines.append('')
        _write_section('Expenses', data.get('expenses', []), data.get('total_expenses', 0))
        lines.append('=' * 66)
        lines.append(f'{"NET INCOME":<50} {ReportExporter._fmt(data.get("net_income", 0)):>14}')

        if data.get('comparison'):
            comp = data['comparison']
            lines.append('')
            lines.append(f'COMPARISON PERIOD: {comp["start_date"]} to {comp["end_date"]}')
            lines.append(f'  Revenue: {ReportExporter._fmt(comp["total_revenue"])} (Growth: {data.get("revenue_growth_pct", 0):.1f}%)')
            lines.append(f'  Net Income: {ReportExporter._fmt(comp["net_income"])} (Growth: {data.get("net_income_growth_pct", 0):.1f}%)')

    @staticmethod
    def _format_balance_sheet_text(lines, data):
        def _write_section(title, sections, total):
            lines.append(title)
            for section in sections:
                lines.append(f'  {section.get("category", ""):<48} {ReportExporter._fmt(section.get("total", 0)):>14}')
                for acc in section.get('accounts', []):
                    lines.append(f'    {acc["account_code"]} - {acc["account_name"]:<40} {ReportExporter._fmt(acc["amount"]):>14}')
            lines.append(f'  {"Total " + title:<48} {ReportExporter._fmt(total):>14}')
            lines.append('')

        _write_section('ASSETS', data.get('assets', {}).get('sections', []), data.get('assets', {}).get('total', 0))
        _write_section('LIABILITIES', data.get('liabilities', {}).get('sections', []), data.get('liabilities', {}).get('total', 0))
        _write_section('EQUITY', data.get('equity', {}).get('sections', []), data.get('equity', {}).get('total', 0))

        lines.append('=' * 66)
        lines.append(f'{"Total Liabilities + Equity":<50} {ReportExporter._fmt(data.get("total_liabilities_equity", 0)):>14}')
        lines.append(f'Difference: {ReportExporter._fmt(data.get("difference", 0))} | {"BALANCED" if data.get("is_balanced") else "NOT BALANCED"}')

    @staticmethod
    def _format_ledger_text(lines, data):
        lines.append(f'Account: {data.get("account_code", "")} - {data.get("account_name", "")}')
        lines.append(f'Opening Balance: {ReportExporter._fmt(data.get("opening_balance", 0))}')
        lines.append('')
        lines.append(f'{"Entry #":<15} {"Date":<12} {"Type":<12} {"Debit":>12} {"Credit":>12} {"Balance":>12}')
        lines.append('-' * 77)
        for entry in data.get('entries', []):
            lines.append(f'{entry["entry_number"]:<15} {entry["entry_date"]:<12} {entry["entry_type"]:<12} {ReportExporter._fmt(entry["debit"]):>12} {ReportExporter._fmt(entry["credit"]):>12} {ReportExporter._fmt(entry["running_balance"]):>12}')
        lines.append('-' * 77)
        lines.append(f'Closing Balance: {ReportExporter._fmt(data.get("closing_balance", 0))} ({data.get("entry_count", 0)} entries)')

    @staticmethod
    def _format_cash_flow_text(lines, data):
        op = data.get('operating_activities', {})
        lines.append(f'{"Net Income":<50} {ReportExporter._fmt(op.get("net_income", 0)):>14}')
        for item in op.get('working_capital_changes', []):
            lines.append(f'  {item.get("description", ""):<48} {ReportExporter._fmt(item.get("change", 0)):>14}')
        lines.append(f'{"Net Cash from Operations":<50} {ReportExporter._fmt(op.get("net_cash_from_operations", 0)):>14}')
        lines.append('')

        inv = data.get('investing_activities', {})
        for item in inv.get('items', []):
            lines.append(f'  {item.get("description", ""):<48} {ReportExporter._fmt(item.get("change", 0)):>14}')
        lines.append(f'{"Net Cash from Investing":<50} {ReportExporter._fmt(inv.get("net_cash_from_investing", 0)):>14}')
        lines.append('')

        fin = data.get('financing_activities', {})
        for item in fin.get('items', []):
            lines.append(f'  {item.get("description", ""):<48} {ReportExporter._fmt(item.get("change", 0)):>14}')
        lines.append(f'{"Net Cash from Financing":<50} {ReportExporter._fmt(fin.get("net_cash_from_financing", 0)):>14}')
        lines.append('')
        lines.append(f'{"Net Change in Cash":<50} {ReportExporter._fmt(data.get("net_change_in_cash", 0)):>14}')
        lines.append(f'{"Opening Cash Balance":<50} {ReportExporter._fmt(data.get("opening_cash_balance", 0)):>14}')
        lines.append(f'{"Closing Cash Balance":<50} {ReportExporter._fmt(data.get("closing_cash_balance", 0)):>14}')

    @staticmethod
    def _format_ar_aging_text(lines, data):
        lines.append(f'{"Customer":<30} {"Current":>10} {"1-30d":>10} {"31-60d":>10} {"61-90d":>10} {"90+d":>10} {"Total":>12}')
        lines.append('-' * 94)
        for row in data.get('aging_rows', []):
            lines.append(f'{row.get("party_name", ""):<30} {ReportExporter._fmt(row.get("current", 0)):>10} {ReportExporter._fmt(row.get("age_1_30", 0)):>10} {ReportExporter._fmt(row.get("age_31_60", 0)):>10} {ReportExporter._fmt(row.get("age_61_90", 0)):>10} {ReportExporter._fmt(row.get("age_90_plus", 0)):>10} {ReportExporter._fmt(row.get("total", 0)):>12}')
        totals = data.get('totals', {})
        lines.append('-' * 94)
        lines.append(f'{"TOTAL":<30} {ReportExporter._fmt(totals.get("current", 0)):>10} {ReportExporter._fmt(totals.get("age_1_30", 0)):>10} {ReportExporter._fmt(totals.get("age_31_60", 0)):>10} {ReportExporter._fmt(totals.get("age_61_90", 0)):>10} {ReportExporter._fmt(totals.get("age_90_plus", 0)):>10} {ReportExporter._fmt(totals.get("total", 0)):>12}')

    @staticmethod
    def _format_ap_aging_text(lines, data):
        lines.append(f'{"Supplier":<30} {"Current":>10} {"1-30d":>10} {"31-60d":>10} {"61-90d":>10} {"90+d":>10} {"Total":>12}')
        lines.append('-' * 94)
        for row in data.get('aging_rows', []):
            lines.append(f'{row.get("party_name", ""):<30} {ReportExporter._fmt(row.get("current", 0)):>10} {ReportExporter._fmt(row.get("age_1_30", 0)):>10} {ReportExporter._fmt(row.get("age_31_60", 0)):>10} {ReportExporter._fmt(row.get("age_61_90", 0)):>10} {ReportExporter._fmt(row.get("age_90_plus", 0)):>10} {ReportExporter._fmt(row.get("total", 0)):>12}')
        totals = data.get('totals', {})
        lines.append('-' * 94)
        lines.append(f'{"TOTAL":<30} {ReportExporter._fmt(totals.get("current", 0)):>10} {ReportExporter._fmt(totals.get("age_1_30", 0)):>10} {ReportExporter._fmt(totals.get("age_31_60", 0)):>10} {ReportExporter._fmt(totals.get("age_61_90", 0)):>10} {ReportExporter._fmt(totals.get("age_90_plus", 0)):>10} {ReportExporter._fmt(totals.get("total", 0)):>12}')

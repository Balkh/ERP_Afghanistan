"""Payslip generation and preview dialog."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTextEdit,
                                QLabel, QFileDialog, QWidget)
from PySide6.QtGui import QFont
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    TEXT_BODY, TEXT_CARD_TITLE, TEXT_SECTION_TITLE,
    COLOR_PRIMARY, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_ON_PRIMARY, COLOR_TEXT_MUTED, COLOR_BG_SURFACE, COLOR_BORDER,
    BORDER_RADIUS_LG,
)


class PayslipDialog(EnterpriseDialog):
    """Dialog for previewing and printing payslips."""

    def __init__(self, parent=None, payslip_data=None):
        self.payslip_data = payslip_data or {}
        super().__init__("Payslip Preview", DialogType.CUSTOM, parent)
        self.setModal(True)
        self.resize(800, 650)
        content = self._build_content()
        self.set_content(content)
        self._render_payslip()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        title_layout = QHBoxLayout()
        title_label = QLabel("Payslip Preview")
        title_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(450)
        layout.addWidget(self.preview, 1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(SPACING_SM)

        self.print_btn = EnterpriseButton("Print", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.print_btn.clicked.connect(self._print_payslip)

        self.print_preview_btn = EnterpriseButton("Print Preview", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.print_preview_btn.clicked.connect(self._print_preview)

        self.save_pdf_btn = EnterpriseButton("Export PDF", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.save_pdf_btn.clicked.connect(self._save_as_pdf)

        close_btn = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.print_preview_btn)
        button_layout.addWidget(self.save_pdf_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        return widget

    def _render_payslip(self):
        """Render the payslip as styled HTML."""
        data = self.payslip_data
        company_name = data.get("company_name", "Pharmacy ERP")
        employee_name = data.get("employee_name", "N/A")
        department = data.get("department", "N/A")
        position = data.get("position", "N/A")
        period = data.get("period", "N/A")
        basic_salary = data.get("basic_salary", 0)
        currency = data.get("currency", "AFN")

        earnings = data.get("earnings", [])
        deductions = data.get("deductions", [])
        total_earnings = data.get("total_earnings", sum(e.get("amount", 0) for e in earnings))
        total_deductions = data.get("total_deductions", sum(d.get("amount", 0) for d in deductions))
        net_pay = data.get("net_pay", total_earnings - total_deductions)

        earnings_rows = ""
        for item in earnings:
            earnings_rows += f"""
                <tr>
                    <td style="padding: 8px 10px; border-bottom: 1px solid {COLOR_BORDER}; color: {COLOR_TEXT_PRIMARY};">{item.get("label", "")}</td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid {COLOR_BORDER}; text-align: right; color: {COLOR_TEXT_PRIMARY};">{currency} {item.get("amount", 0):,.2f}</td>
                </tr>
            """

        deductions_rows = ""
        for item in deductions:
            deductions_rows += f"""
                <tr>
                    <td style="padding: 8px 10px; border-bottom: 1px solid {COLOR_BORDER}; color: {COLOR_TEXT_PRIMARY};">{item.get("label", "")}</td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid {COLOR_BORDER}; text-align: right; color: {COLOR_TEXT_PRIMARY};">{currency} {item.get("amount", 0):,.2f}</td>
                </tr>
            """

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: {SPACING_XL}px; font-size: {TEXT_BODY}px; color: {COLOR_TEXT_PRIMARY}; background-color: {COLOR_BG_SURFACE}; }}
                .header {{ background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_XL}px; border-radius: {BORDER_RADIUS_LG}px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: {TEXT_SECTION_TITLE}px; }}
                .header p {{ margin: {SPACING_SM}px 0 0 0; opacity: 0.9; }}
                .info-grid {{ display: flex; justify-content: space-between; margin: {SPACING_XL}px 0; gap: {SPACING_LG}px; }}
                .info-grid .info-box {{ flex: 1; background: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; padding: {SPACING_MD}px {SPACING_LG}px; }}
                .info-grid .info-box p {{ margin: {SPACING_SM}px 0; font-size: {TEXT_BODY}px; }}
                .info-grid .info-box strong {{ color: {COLOR_TEXT_SECONDARY}; }}
                .columns {{ display: flex; gap: {SPACING_LG}px; margin: {SPACING_XL}px 0; }}
                .columns .col {{ flex: 1; background: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; overflow: hidden; }}
                .col-header {{ background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px {SPACING_LG}px; font-weight: 700; font-size: {TEXT_BODY}px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_SM}px 10px; text-align: left; font-weight: 600; font-size: {TEXT_BODY}px; }}
                td {{ padding: 8px 10px; border-bottom: 1px solid {COLOR_BORDER}; color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}px; }}
                .total-row td {{ font-weight: 700; background-color: {COLOR_BG_SURFACE}; border-top: 2px solid {COLOR_BORDER}; }}
                .net-pay {{ background-color: {COLOR_PRIMARY}; color: {COLOR_TEXT_ON_PRIMARY}; text-align: center; padding: {SPACING_MD}px {SPACING_LG}px; border-radius: {BORDER_RADIUS_LG}px; margin: {SPACING_XL}px 0; }}
                .net-pay h2 {{ margin: 0; font-size: {TEXT_SECTION_TITLE}px; }}
                .net-pay .amount {{ font-size: {TEXT_SECTION_TITLE}px; font-weight: 700; margin-top: {SPACING_SM}px; }}
                .footer {{ text-align: center; margin-top: {SPACING_XL}px; color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}px; border-top: 1px solid {COLOR_BORDER}; padding-top: {SPACING_MD}px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{company_name}</h1>
                <p>Salary Payslip</p>
            </div>

            <div class="info-grid">
                <div class="info-box">
                    <p><strong>Employee:</strong> {employee_name}</p>
                    <p><strong>Department:</strong> {department}</p>
                </div>
                <div class="info-box">
                    <p><strong>Period:</strong> {period}</p>
                    <p><strong>Position:</strong> {position}</p>
                </div>
            </div>

            <div class="columns">
                <div class="col">
                    <div class="col-header">EARNINGS</div>
                    <table>
                        <thead>
                            <tr><th style="text-align:left;">Description</th><th style="text-align:right;">Amount</th></tr>
                        </thead>
                        <tbody>
                            {earnings_rows}
                            <tr class="total-row">
                                <td style="padding: 8px 10px;">Total Earnings</td>
                                <td style="padding: 8px 10px; text-align: right;">{currency} {total_earnings:,.2f}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col">
                    <div class="col-header">DEDUCTIONS</div>
                    <table>
                        <thead>
                            <tr><th style="text-align:left;">Description</th><th style="text-align:right;">Amount</th></tr>
                        </thead>
                        <tbody>
                            {deductions_rows}
                            <tr class="total-row">
                                <td style="padding: 8px 10px;">Total Deductions</td>
                                <td style="padding: 8px 10px; text-align: right;">{currency} {total_deductions:,.2f}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="net-pay">
                <h2>NET PAY</h2>
                <div class="amount">{currency} {net_pay:,.2f}</div>
            </div>

            <div class="footer">
                <p>This is a computer-generated payslip from {company_name} HR System</p>
            </div>
        </body>
        </html>
        """

        self.preview.setHtml(html)

    def _print_payslip(self):
        """Print the payslip directly."""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self.preview.print_(printer)

    def _print_preview(self):
        """Show print preview."""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(self.preview.print_)
        dialog.exec()

    def _save_as_pdf(self):
        """Export payslip as PDF."""
        employee_name = self.payslip_data.get("employee_name", "employee").replace(" ", "_")
        period = self.payslip_data.get("period", "draft").replace(" ", "_")
        default_filename = f"Payslip_{employee_name}_{period}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Payslip as PDF",
            default_filename,
            "PDF Files (*.pdf)"
        )

        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self.preview.print_(printer)
            AlertDialog.info("Success", f"Payslip exported to:\n{file_path}", self)

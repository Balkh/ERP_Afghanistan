"""SECTION: Workflows Validation — extracted from gate_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
import importlib
import logging
import os
import sys
import json
import time
import threading
import hashlib
import uuid
from decimal import Decimal
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from production_gate.gate_validator import (
    GateIssue, SectionResult, ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW, logger,
)


def simulate_accountant_workflow() -> List[GateIssue]:
    issues = []
    try:
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from decimal import Decimal

        entry_count_before = JournalEntry.objects.count()

        je = JournalEntry.objects.create(
            entry_number=f"GATE-{uuid.uuid4().hex[:8]}",
            entry_date=date.today(),
            entry_type="ADJUSTMENT",
            description="Production gate test entry",
            is_posted=True,
        )
        cash = Account.objects.filter(code="1000").first()
        equity = Account.objects.filter(account_type="EQUITY").first()

        if cash and equity and je:
            JournalEntryLine.objects.create(
                entry=je, account=cash, debit=Decimal("1000.00"), credit=Decimal("0.00"),
                description="Gate test debit",
            )
            JournalEntryLine.objects.create(
                entry=je, account=equity, debit=Decimal("0.00"), credit=Decimal("1000.00"),
                description="Gate test credit",
            )

            balanced = je.is_balanced
            if not balanced:
                issues.append(GateIssue(
                    section="workflow_accountant", severity=ISSUE_CRITICAL,
                    check="journal_balance",
                    detail=f"Posted journal entry {je.entry_number} is not balanced",
                ))

            try:
                je2 = JournalEntry.objects.create(
                    entry_number=f"GATE-REV-{uuid.uuid4().hex[:8]}",
                    entry_date=date.today(),
                    entry_type="REVERSAL",
                    description="Gate test reversal",
                    is_posted=True,
                    original_entry=je,
                )
                JournalEntryLine.objects.create(
                    entry=je2, account=cash, debit=Decimal("0.00"), credit=Decimal("1000.00"),
                )
                JournalEntryLine.objects.create(
                    entry=je2, account=equity, debit=Decimal("1000.00"), credit=Decimal("0.00"),
                )
            except Exception as e:
                issues.append(GateIssue(
                    section="workflow_accountant", severity=ISSUE_MEDIUM,
                    check="journal_reversal", detail=f"Reversal failed: {e}",
                ))

            from accounting.services.financial_reports import FinancialReportEngine
            try:
                tb = FinancialReportEngine.get_trial_balance()
                issues.append(GateIssue(
                    section="workflow_accountant", severity=ISSUE_LOW,
                    check="report_generation", detail="Trial balance generated", passed=True,
                ))
            except Exception:
                pass

        if not cash:
            issues.append(GateIssue(
                section="workflow_accountant", severity=ISSUE_MEDIUM,
                check="account_availability", detail="Cash account (1000) not found",
            ))

    except Exception as e:
        issues.append(GateIssue(
            section="workflow_accountant", severity=ISSUE_CRITICAL,
            check="workflow_execution", detail=f"Accountant workflow crashed: {e}",
        ))
    return issues



def simulate_cashier_workflow() -> List[GateIssue]:
    issues = []
    try:
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from decimal import Decimal

        cash = Account.objects.filter(code="1000").first()
        revenue = Account.objects.filter(account_type="REVENUE").first()

        if cash and revenue:
            cash_bal_before = cash.balance
            je = JournalEntry.objects.create(
                entry_number=f"GATE-CASH-{uuid.uuid4().hex[:8]}",
                entry_date=date.today(),
                entry_type="RECEIPT",
                description="Gate test cash sale",
                is_posted=True,
            )
            JournalEntryLine.objects.create(
                entry=je, account=cash, debit=Decimal("500.00"), credit=Decimal("0.00"),
            )
            JournalEntryLine.objects.create(
                entry=je, account=revenue, debit=Decimal("0.00"), credit=Decimal("500.00"),
            )

            if not je.is_balanced:
                issues.append(GateIssue(
                    section="workflow_cashier", severity=ISSUE_CRITICAL,
                    check="cash_sale_balance",
                    detail="Cash sale journal entry not balanced",
                ))

            issues.append(GateIssue(
                section="workflow_cashier", severity=ISSUE_LOW,
                check="cash_sale", detail="Cash sale workflow completed", passed=True,
            ))
        else:
            issues.append(GateIssue(
                section="workflow_cashier", severity=ISSUE_MEDIUM,
                check="account_availability",
                detail=f"Cash (1000) or Revenue account not found",
            ))
    except Exception as e:
        issues.append(GateIssue(
            section="workflow_cashier", severity=ISSUE_CRITICAL,
            check="workflow_execution", detail=f"Cashier workflow crashed: {e}",
        ))
    return issues



def simulate_warehouse_workflow() -> List[GateIssue]:
    issues = []
    try:
        from inventory.models import Product, Batch, StockMovement, Warehouse, Category, Unit
        from decimal import Decimal

        cat = Category.objects.first()
        unit = Unit.objects.first()
        warehouse = Warehouse.objects.first()
        product = Product.objects.first()

        if not cat:
            cat = Category.objects.create(name="Gate Test Category")
        if not unit:
            unit = Unit.objects.create(name="Piece", symbol="pc")
        if not warehouse:
            warehouse = Warehouse.objects.create(name="Gate WH", code="GWH1")
        if not product:
            product = Product.objects.create(
                name="Gate Test Product", generic_name="GTP", brand_name="GTP",
                category=cat, unit=unit, strength="10mg", form="Tab",
                manufacturer="Gate", barcode=f"GATE{uuid.uuid4().hex[:8]}",
                sku=f"SKU-GATE-{uuid.uuid4().hex[:6]}",
            )

        batch = Batch.objects.create(
            product=product,
            batch_number=f"BATCH-GATE-{uuid.uuid4().hex[:8]}",
            manufacturing_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
            purchase_price=Decimal("50.00"),
            sale_price=Decimal("100.00"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            location="Gate Shelf",
        )

        if batch.remaining_quantity != batch.quantity:
            issues.append(GateIssue(
                section="workflow_warehouse", severity=ISSUE_HIGH,
                check="batch_initial_qty",
                detail=f"Batch initial qty mismatch: remaining={batch.remaining_quantity} != quantity={batch.quantity}",
            ))

        # Create IN movement first so _update_batch_quantity has a base
        StockMovement.objects.create(
            product=product, batch=batch, warehouse=warehouse,
            movement_type="IN", reference_type="PURCHASE",
            quantity=Decimal("100"), unit_cost=Decimal("50.00"),
        )

        movement = StockMovement.objects.create(
            product=product, batch=batch, warehouse=warehouse,
            movement_type="OUT", reference_type="SALE",
            quantity=Decimal("-10"), unit_cost=Decimal("50.00"),
        )

        batch.refresh_from_db()
        if batch.remaining_quantity != Decimal("90"):
            issues.append(GateIssue(
                section="workflow_warehouse", severity=ISSUE_HIGH,
                check="stock_movement_qty",
                detail=f"After OUT -10, remaining={batch.remaining_quantity}, expected=90",
            ))

        issues.append(GateIssue(
            section="workflow_warehouse", severity=ISSUE_LOW,
            check="stock_receipt_and_issue", detail="Warehouse workflow completed", passed=True,
        ))
    except Exception as e:
        issues.append(GateIssue(
            section="workflow_warehouse", severity=ISSUE_CRITICAL,
            check="workflow_execution", detail=f"Warehouse workflow crashed: {e}",
        ))
    return issues



def simulate_hr_workflow() -> List[GateIssue]:
    issues = []
    try:
        from hr.models import Employee, Department, Position
        from payroll.models import PayrollCycle, SalaryStructure

        dept = Department.objects.first()
        if not dept:
            dept = Department.objects.create(name="Gate Test Dept", code="GTD")

        pos = Position.objects.first()
        if not pos:
            pos = Position.objects.create(title="Gate Tester", code="GT")

        emp = Employee.objects.create(
            employee_code=f"EMP-GATE-{uuid.uuid4().hex[:6]}",
            first_name="Gate", last_name="Tester",
            department=dept, position=pos,
            employment_status="active",
        )

        issues.append(GateIssue(
            section="workflow_hr", severity=ISSUE_LOW,
            check="employee_onboarding", detail=f"Employee {emp.employee_code} created", passed=True,
        ))

        ss = SalaryStructure.objects.create(
            employee=emp, basic_salary=Decimal("30000"),
        )

        cycle = PayrollCycle.objects.create(
            name="Gate Test Payroll", period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31), status="completed",
        )

        issues.append(GateIssue(
            section="workflow_hr", severity=ISSUE_LOW,
            check="payroll_processing", detail="Payroll cycle created", passed=True,
        ))

    except Exception as e:
        issues.append(GateIssue(
            section="workflow_hr", severity=ISSUE_MEDIUM,
            check="workflow_execution", detail=f"HR workflow: {e}",
        ))
    return issues



def _wf_ok(section: str, issues: List[GateIssue]) -> str:
    crit = [i for i in issues if i.section == section and i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]
    return "OK" if not crit else f"{len(crit)} issues"

# ── SECTION 3: CONCURRENCY + STRESS TESTING ─────────────────────────



def run(self) -> SectionResult:
    all_issues = []
    all_issues.extend(simulate_accountant_workflow())
    all_issues.extend(simulate_cashier_workflow())
    all_issues.extend(simulate_warehouse_workflow())
    all_issues.extend(simulate_hr_workflow())

    high_crit = [i for i in all_issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]
    passed = len(high_crit) == 0
    self.results["workflow_validation"] = SectionResult(
        name="Human Workflow Simulation",
        passed=passed,
        issues=all_issues,
        detail=f"4 workflows: accountant={_wf_ok('workflow_accountant', all_issues)}, "
               f"cashier={_wf_ok('workflow_cashier', all_issues)}, "
               f"warehouse={_wf_ok('workflow_warehouse', all_issues)}, "
               f"hr={_wf_ok('workflow_hr', all_issues)}",
    )
    self.issues.extend(all_issues)
    return self.results["workflow_validation"]


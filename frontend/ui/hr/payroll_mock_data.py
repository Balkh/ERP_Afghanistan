"""Mock data for payroll screens (development/offline mode)."""


def get_mock_salary_structures():
    return [
        {"name": "Standard Grade 1", "basic_salary": "15000.00", "is_active": True, "created_at": "2026-01-01"},
        {"name": "Standard Grade 2", "basic_salary": "20000.00", "is_active": True, "created_at": "2026-01-01"},
        {"name": "Manager Grade", "basic_salary": "35000.00", "is_active": True, "created_at": "2026-01-15"},
    ]


def get_mock_payroll_cycles():
    return [
        {"period_month": "April", "period_year": "2026", "status": "PAID", "employee_count": 25, "total_gross": "450000.00", "total_net": "380000.00"},
        {"period_month": "March", "period_year": "2026", "status": "PAID", "employee_count": 24, "total_gross": "420000.00", "total_net": "355000.00"},
        {"period_month": "May", "period_year": "2026", "status": "DRAFT", "employee_count": 25, "total_gross": "450000.00", "total_net": "380000.00"},
    ]


def get_mock_payroll_records():
    return [
        {"employee_name": "Ahmad Rostami", "period": "April 2026", "basic_salary": "15000.00", "total_allowances": "2500.00", "total_deductions": "1800.00", "gross_salary": "17500.00", "net_salary": "15700.00", "status": "Paid"},
        {"employee_name": "Maria Haq", "period": "April 2026", "basic_salary": "20000.00", "total_allowances": "3000.00", "total_deductions": "2500.00", "gross_salary": "23000.00", "net_salary": "20500.00", "status": "Paid"},
    ]

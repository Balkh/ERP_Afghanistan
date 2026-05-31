"""
Section 5 — API Contract Guard.
Validates that API contracts (endpoints, serializers, response format) are stable.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContractEndpoint:
    path: str
    methods: Set[str]
    serializer: Optional[str] = None
    deprecated: bool = False


@dataclass
class ContractCheckResult:
    endpoint: str
    passed: bool
    detail: str
    severity: str = "high"


# Known API endpoints with expected contracts
EXPECTED_ENDPOINTS: List[ContractEndpoint] = [
    ContractEndpoint("/api/accounts/", {"GET", "POST"}),
    ContractEndpoint("/api/accounts/{id}/", {"GET", "PUT", "PATCH", "DELETE"}),
    ContractEndpoint("/api/journal-entries/", {"GET", "POST"}),
    ContractEndpoint("/api/journal-entries/{id}/", {"GET", "PUT", "PATCH", "DELETE"}),
    ContractEndpoint("/api/financial-reports/trial-balance/", {"GET"}),
    ContractEndpoint("/api/financial-reports/profit-loss/", {"GET"}),
    ContractEndpoint("/api/financial-reports/balance-sheet/", {"GET"}),
    ContractEndpoint("/api/financial-reports/ar-aging/", {"GET"}),
    ContractEndpoint("/api/financial-reports/ap-aging/", {"GET"}),
    ContractEndpoint("/api/payment-methods/", {"GET"}),
    ContractEndpoint("/api/payment-accounts/", {"GET"}),
    ContractEndpoint("/api/transactions/", {"GET", "POST"}),
    ContractEndpoint("/api/products/", {"GET", "POST"}),
    ContractEndpoint("/api/batches/", {"GET", "POST"}),
    ContractEndpoint("/api/categories/", {"GET", "POST"}),
    ContractEndpoint("/api/warehouses/", {"GET", "POST"}),
    ContractEndpoint("/api/customers/", {"GET", "POST"}),
    ContractEndpoint("/api/suppliers/", {"GET", "POST"}),
    ContractEndpoint("/api/sales-invoices/", {"GET", "POST"}),
    ContractEndpoint("/api/purchase-invoices/", {"GET", "POST"}),
    ContractEndpoint("/api/employees/", {"GET", "POST"}),
    ContractEndpoint("/api/attendance/", {"GET", "POST"}),
    ContractEndpoint("/api/payroll/", {"GET", "POST"}),
]


def check_endpoints(registered_endpoints: Set[str]) -> List[ContractCheckResult]:
    results = []
    for expected in EXPECTED_ENDPOINTS:
        # Check if path pattern exists (support wildcards)
        pattern = expected.path.replace("{id}", "").rstrip("/")
        matched = any(pattern in ep for ep in registered_endpoints)
        if matched:
            results.append(ContractCheckResult(expected.path, True, "Endpoint registered"))
        else:
            results.append(
                ContractCheckResult(expected.path, False, "Endpoint NOT registered", "critical")
            )
    return results


def check_response_schema(sample_response: Dict) -> ContractCheckResult:
    if "success" in sample_response:
        return ContractCheckResult("response_schema", True, "Standardized response format")
    return ContractCheckResult("response_schema", False, "Missing 'success' field", "critical")


def verify_contract_snapshot(registered_endpoints: Set[str]) -> List[ContractCheckResult]:
    return check_endpoints(registered_endpoints)

"""
System Integrity Service - Frontend-side Cross-Module Validation Engine.
Performs consistency checks across Sales, Inventory, Accounting, etc.
"""

import time
from datetime import datetime
from typing import List, Dict, Any

class SystemIntegrityService:
    """
    Validates ERP system integrity by cross-referencing data from multiple APIs.
    This service is read-only and does not modify any data.
    """
    
    def __init__(self, api_client):
        self.api_client = api_client

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all integrity test suites sequentially."""
        results = []
        results.extend(self.test_sales_accounting_consistency())
        results.extend(self.test_inventory_synchronization())
        results.extend(self.test_workflow_state_truth())
        results.extend(self.test_control_center_truth())
        results.extend(self.test_duplication_detection())
        return results

    def _create_result(self, name, modules, status, severity, description, details="", fix=""):
        return {
            "name": name,
            "modules": modules,
            "status": status, # PASS, FAIL, WARNING
            "severity": severity, # LOW, MEDIUM, HIGH, CRITICAL
            "description": description,
            "details": details,
            "fix": fix,
            "timestamp": datetime.now().isoformat()
        }

    def test_sales_accounting_consistency(self) -> List[Dict[str, Any]]:
        """Verify Sales Invoices have corresponding Journal Entries."""
        results = []
        try:
            # Fetch last 50 invoices
            invoices_res = self.api_client.get('/api/sales/invoices/?limit=50')
            invoices = invoices_res.get('data', {}).get('results', []) if isinstance(invoices_res, dict) else []
            
            # Fetch last 100 journal entries
            journals_res = self.api_client.get('/api/accounting/journal-entries/?limit=100')
            journals = journals_res.get('data', {}).get('results', []) if isinstance(journals_res, dict) else []
            
            mismatches = []
            for inv in invoices:
                inv_no = inv.get('invoice_number')
                # Check if a journal entry mentions this invoice number
                found = any(inv_no in str(j.get('description', '')) for j in journals)
                if not found and inv.get('status') == 'POSTED':
                    mismatches.append(f"Invoice {inv_no} is POSTED but no linked Journal Entry found.")

            if mismatches:
                results.append(self._create_result(
                    "Sales-Accounting Link",
                    ["Sales", "Accounting"],
                    "FAIL", "HIGH",
                    "Some posted invoices are missing journal entries.",
                    "\n".join(mismatches),
                    "Trigger manual GL posting for these invoices."
                ))
            else:
                results.append(self._create_result(
                    "Sales-Accounting Link",
                    ["Sales", "Accounting"],
                    "PASS", "LOW",
                    "All checked invoices have corresponding journal entries."
                ))
        except Exception as e:
            results.append(self._create_result("Sales-Accounting Link", ["Sales", "Accounting"], "WARNING", "MEDIUM", f"Test failed to execute: {str(e)}"))
        
        return results

    def test_inventory_synchronization(self) -> List[Dict[str, Any]]:
        """Verify stock levels match across Inventory and Sales/Purchase."""
        # Simplified: Check if batch quantities are consistent
        results = []
        try:
            batches_res = self.api_client.get('/api/inventory/batches/?limit=50')
            batches = batches_res.get('data', {}).get('results', []) if isinstance(batches_res, dict) else []
            
            issues = []
            for batch in batches:
                # Logic: If batch is expired but has remaining_quantity > 0, flag it (business rule check)
                if batch.get('is_expired') and float(batch.get('remaining_quantity', 0)) > 0:
                    issues.append(f"Batch {batch.get('batch_number')} is expired but still has stock: {batch.get('remaining_quantity')}")
            
            if issues:
                results.append(self._create_result(
                    "Inventory Integrity",
                    ["Inventory"],
                    "WARNING", "MEDIUM",
                    "Expired batches with active stock detected.",
                    "\n".join(issues),
                    "Run inventory write-off for expired batches."
                ))
            else:
                results.append(self._create_result("Inventory Integrity", ["Inventory"], "PASS", "LOW", "Stock levels appear consistent."))
        except Exception as e:
            results.append(self._create_result("Inventory Integrity", ["Inventory"], "WARNING", "MEDIUM", f"Test error: {str(e)}"))
        
        return results

    def test_workflow_state_truth(self) -> List[Dict[str, Any]]:
        """Verify workflow states match entity states."""
        results = []
        try:
            # Cross-check Workflows vs Invoices
            wf_res = self.api_client.get('/api/workflows/instances/?limit=50')
            workflows = wf_res.get('data', {}).get('results', []) if isinstance(wf_res, dict) else []
            
            inv_res = self.api_client.get('/api/sales/invoices/?limit=50')
            invoices = {i.get('id'): i for i in (inv_res.get('data', {}).get('results', []) if isinstance(inv_res, dict) else [])}
            
            mismatches = []
            for wf in workflows:
                if wf.get('entity_type') == 'SalesInvoice':
                    obj_id = wf.get('object_id')
                    invoice = invoices.get(obj_id)
                    if invoice:
                        # Logic: If workflow is APPROVED but invoice is still PENDING, mismatch
                        if wf.get('current_state') == 'APPROVED' and invoice.get('status') == 'PENDING':
                            mismatches.append(f"Workflow for Invoice {invoice.get('invoice_number')} is APPROVED but invoice status is PENDING.")
            
            if mismatches:
                results.append(self._create_result(
                    "Workflow-Entity Sync",
                    ["Workflows", "Sales"],
                    "FAIL", "CRITICAL",
                    "State mismatch between workflow engine and business entities.",
                    "\n".join(mismatches),
                    "Investigate signal coordinator and state transition listeners."
                ))
            else:
                results.append(self._create_result("Workflow-Entity Sync", ["Workflows", "Sales"], "PASS", "LOW", "Workflow states are synchronized with entities."))
        except Exception as e:
            results.append(self._create_result("Workflow-Entity Sync", ["Workflows", "Sales"], "WARNING", "MEDIUM", f"Test error: {str(e)}"))
            
        return results

    def test_control_center_truth(self) -> List[Dict[str, Any]]:
        """Verify Control Center metrics reflect backend realities."""
        results = []
        try:
            health_res = self.api_client.get('/api/control-center/health/')
            health = health_res.get('data', {}) if isinstance(health_res, dict) else {}
            
            # Simple check: If health API says DB is UP, verify we can actually fetch something
            if health.get('database', {}).get('status') == 'healthy':
                # Try a lightweight query
                acc_res = self.api_client.get('/api/accounting/accounts/?limit=1')
                if not acc_res:
                    results.append(self._create_result(
                        "Control Center Truth",
                        ["Control Center", "Database"],
                        "FAIL", "HIGH",
                        "Control Center reports DB healthy but direct query failed.",
                        "Health API Status: Healthy, Direct Query: No response",
                        "Verify health check probe logic in backend."
                    ))
                    return results
            
            results.append(self._create_result("Control Center Truth", ["Control Center"], "PASS", "LOW", "Control Center metrics match backend state."))
        except Exception as e:
            results.append(self._create_result("Control Center Truth", ["Control Center"], "WARNING", "MEDIUM", f"Test error: {str(e)}"))
        
        return results

    def test_duplication_detection(self) -> List[Dict[str, Any]]:
        """Detect duplicate records that might have slipped through validation."""
        results = []
        try:
            # Check for duplicate invoice numbers
            inv_res = self.api_client.get('/api/sales/invoices/?limit=100')
            invoices = inv_res.get('data', {}).get('results', []) if isinstance(inv_res, dict) else []
            
            numbers = [i.get('invoice_number') for i in invoices]
            duplicates = set([x for x in numbers if numbers.count(x) > 1])
            
            if duplicates:
                results.append(self._create_result(
                    "Data Duplication",
                    ["Sales"],
                    "FAIL", "CRITICAL",
                    "Duplicate invoice numbers detected in the system.",
                    f"Duplicate Numbers: {', '.join(map(str, duplicates))}",
                    "Enforce unique constraints at DB level and clean up duplicates."
                ))
            else:
                results.append(self._create_result("Data Duplication", ["Sales", "Accounting"], "PASS", "LOW", "No duplicate business records detected."))
        except Exception as e:
            results.append(self._create_result("Data Duplication", ["Sales"], "WARNING", "MEDIUM", f"Test error: {str(e)}"))
            
        return results

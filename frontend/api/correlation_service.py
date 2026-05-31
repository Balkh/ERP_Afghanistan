"""
Correlation Intelligence Service - Cross-System Event Correlation Engine.
Aggregates data from Sales, Accounting, Inventory, and Workflows into a unified ecosystem.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional

class CorrelationIntelligenceService:
    """
    Connects independent module data into correlated business event chains.
    Provides impact analysis and root cause detection across ERP subsystems.
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.event_chains: List[Dict[str, Any]] = []

    def build_from_prefetched(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Build correlation from hub-bundle sources (no HTTP)."""
        try:
            invoices = sources.get("invoices") or []
            workflows = sources.get("workflows") or []
            journals = sources.get("journals") or []
            payments = sources.get("payments") or []
            chains = []
            for inv in invoices:
                chains.append(
                    self._build_chain_for_invoice(inv, workflows, journals, payments)
                )
            self.event_chains = chains
            score = self._calculate_erp_consistency_score(chains)
            return {
                "status": "ok",
                "consistency_score": score,
                "chains": chains,
                "timestamp": datetime.now().isoformat(),
                "source": "hub_bundle",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def build_correlation_ecosystem(self, parallel: bool = True) -> Dict[str, Any]:
        """
        Fetch data from all modules and correlate them into a single intelligence structure.
        Safe to call from a worker thread when using parallel=True (background HTTP).
        """
        try:
            endpoints = {
                "invoices": "/api/sales/invoices/?limit=20",
                "workflows": "/api/workflows/instances/?limit=50",
                "journals": "/api/accounting/journal-entries/?limit=50",
                "payments": "/api/sales/payments/?limit=20",
            }
            if parallel:
                fetched = self._fetch_all_parallel(endpoints)
            else:
                fetched = {k: self._fetch_data(url) for k, url in endpoints.items()}

            invoices = fetched.get("invoices") or []
            workflows = fetched.get("workflows") or []
            journals = fetched.get("journals") or []
            payments = fetched.get("payments") or []
            partial = any(
                fetched.get(k) is None for k in endpoints
            )  # reserved for future explicit partial flags

            chains = []
            for inv in invoices:
                chain = self._build_chain_for_invoice(inv, workflows, journals, payments)
                chains.append(chain)

            self.event_chains = chains
            score = self._calculate_erp_consistency_score(chains)

            status = "ok" if chains or not partial else "partial"
            return {
                "status": status,
                "consistency_score": score,
                "chains": chains,
                "timestamp": datetime.now().isoformat(),
                "partial": partial,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _fetch_all_parallel(self, endpoints: Dict[str, str]) -> Dict[str, Optional[List[Dict[str, Any]]]]:
        """Fetch multiple endpoints concurrently (intended for worker threads)."""
        results: Dict[str, Optional[List[Dict[str, Any]]]] = {k: [] for k in endpoints}
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {
                pool.submit(self._fetch_data, url): key for key, url in endpoints.items()
            }
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    results[key] = future.result()
                except Exception:
                    results[key] = []
        return results

    def _fetch_data(self, endpoint: str) -> List[Dict[str, Any]]:
        res = self.api_client.get(endpoint, background=True, retries=2)
        if isinstance(res, dict) and res.get("success") is False:
            return []
        if isinstance(res, dict) and "data" in res:
            data = res["data"]
            return data.get("results", data) if isinstance(data, dict) else data
        return res if isinstance(res, list) else []

    def _build_chain_for_invoice(self, inv, workflows, journals, payments) -> Dict[str, Any]:
        inv_id = inv.get('id')
        inv_no = inv.get('invoice_number')
        
        # Link Workflow
        wf = next((w for w in workflows if w.get('object_id') == inv_id), None)
        
        # Link Journal Entry (by description matching invoice number)
        journal = next((j for j in journals if inv_no in str(j.get('description', ''))), None)
        
        # Link Payment
        payment = next((p for p in payments if p.get('invoice') == inv_id), None)
        
        # Calculate local chain health
        steps = [
            {"name": "Creation", "status": "COMPLETED", "mod": "Sales"},
            {"name": "Workflow", "status": "COMPLETED" if wf and wf.get('current_state') == 'APPROVED' else ("PENDING" if wf else "MISSING"), "mod": "Workflows"},
            {"name": "Accounting", "status": "COMPLETED" if journal else "MISSING", "mod": "Accounting"},
            {"name": "Payment", "status": "COMPLETED" if payment else "PENDING", "mod": "Sales/Finance"}
        ]
        
        health = sum(1 for s in steps if s['status'] == 'COMPLETED') / len(steps) * 100
        
        return {
            "id": inv_no,
            "entity": "SalesInvoice",
            "amount": inv.get('total_amount'),
            "status": inv.get('status'),
            "health_score": int(health),
            "steps": steps,
            "nodes": [
                {"id": "inv", "label": inv_no, "type": "Invoice", "status": inv.get('status')},
                {"id": "wf", "label": "Approval", "type": "Workflow", "status": wf.get('current_state') if wf else "NONE"},
                {"id": "gl", "label": "Journal", "type": "Accounting", "status": "POSTED" if journal else "NONE"},
                {"id": "pay", "label": "Payment", "type": "Finance", "status": "PAID" if payment else "NONE"}
            ],
            "links": [("inv", "wf"), ("wf", "gl"), ("gl", "pay")]
        }

    def _calculate_erp_consistency_score(self, chains) -> int:
        if not chains: return 100
        avg_health = sum(c['health_score'] for c in chains) / len(chains)
        return int(avg_health)

    def analyze_impact(self, chain_id: str) -> Dict[str, Any]:
        """Predict downstream impact if a step in the chain is delayed or fails."""
        chain = next((c for c in self.event_chains if c['id'] == chain_id), None)
        if not chain: return {}
        
        impacts = []
        for i, step in enumerate(chain['steps']):
            if step['status'] != 'COMPLETED':
                # Downstream impact
                affected = [s['name'] for s in chain['steps'][i+1:]]
                if affected:
                    impacts.append({
                        "source": step['name'],
                        "affected_modules": [s['mod'] for s in chain['steps'][i+1:]],
                        "severity": "HIGH" if step['status'] == 'MISSING' else "MEDIUM",
                        "description": f"Failure in {step['name']} blocks {', '.join(affected)}"
                    })
        return {"chain_id": chain_id, "impacts": impacts}

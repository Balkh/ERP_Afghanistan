"""
Correlation Intelligence Service - Cross-System Event Correlation Engine.
Aggregates data from Sales, Accounting, Inventory, and Workflows into a unified ecosystem.
"""

from datetime import datetime
from typing import List, Dict, Any

class CorrelationIntelligenceService:
    """
    Connects independent module data into correlated business event chains.
    Provides impact analysis and root cause detection across ERP subsystems.
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.event_chains: List[Dict[str, Any]] = []

    def build_correlation_ecosystem(self) -> Dict[str, Any]:
        """
        Fetch data from all modules and correlate them into a single intelligence structure.
        """
        try:
            # 1. Fetch source data from multiple APIs
            invoices = self._fetch_data('/api/sales/invoices/?limit=20')
            workflows = self._fetch_data('/api/workflows/instances/?limit=50')
            journals = self._fetch_data('/api/accounting/journal-entries/?limit=50')
            payments = self._fetch_data('/api/sales/payments/?limit=20')
            
            # 2. Correlate Invoices with Workflows, Journals, and Payments
            chains = []
            for inv in invoices:
                chain = self._build_chain_for_invoice(inv, workflows, journals, payments)
                chains.append(chain)
            
            self.event_chains = chains
            
            # 3. Calculate Global Consistency Score
            score = self._calculate_erp_consistency_score(chains)
            
            return {
                "status": "ok",
                "consistency_score": score,
                "chains": chains,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _fetch_data(self, endpoint: str) -> List[Dict[str, Any]]:
        res = self.api_client.get(endpoint)
        if isinstance(res, dict) and 'data' in res:
            data = res['data']
            return data.get('results', data) if isinstance(data, dict) else data
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

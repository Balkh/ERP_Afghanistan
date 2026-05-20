"""Financial Policy Engine — Deterministic Governance Layer.

Pure functional engine that evaluates SSOT + FCUE + FICL outputs
against deterministic policy rules and produces DecisionRecords.

All decisions are: ALLOW, WARN, SOFT_BLOCK, HARD_BLOCK, or ESCALATE_MANAGER.
No background workers, no ML, no external services.

Usage:
    decisions = FinancialPolicyEngine.evaluate_customer(customer)
    decisions = FinancialPolicyEngine.evaluate_invoice_creation(customer, amount)
"""
from decimal import Decimal
from datetime import timedelta
from typing import NamedTuple, Optional
from django.utils import timezone
from core.models.decision_record import DecisionRecord


class PolicyDecision(NamedTuple):
    """Single policy decision output."""
    decision_type: str  # ALLOW, WARN, SOFT_BLOCK, HARD_BLOCK, ESCALATE_MANAGER
    risk_score: int  # 0-100
    triggered_rules: list  # list of rule IDs that fired
    explanation: str
    requires_review: bool
    safe_mode: bool  # True if SSOT conflict detected


class FinancialPolicyEngine:
    """Deterministic financial policy governance engine.
    
    Stateless — evaluates current state against rules and returns decisions.
    All decisions are logged to DecisionRecord for audit trail.
    """

    # Rule thresholds
    CREDIT_HARD_BLOCK_THRESHOLD = Decimal('0.95')  # 95% utilization
    CREDIT_WARN_THRESHOLD = Decimal('0.80')  # 80% utilization
    OVERDUE_SOFT_BLOCK_DAYS = 90
    OVERDUE_WARN_DAYS = 30
    ANOMALY_WARN_THRESHOLD = 5
    CASHFLOW_NEGATIVE_MONTHS = 3

    @staticmethod
    def _check_ssot_conflict() -> bool:
        """Check if SSOT has any known conflicts.
        
        Returns True if FCUE derived balance != SSOT control plane balance
        for any active entity.
        """
        from core.services.financial_diagnostics import FinancialDiagnostics
        ssot_check = FinancialDiagnostics.check_ssot_consistency()
        return ssot_check['mismatch_count'] > 0

    @staticmethod
    def _get_customer_risk_score(customer) -> int:
        """Get risk score from CreditRiskIntelligence."""
        from core.services.credit_risk_intelligence import CreditRiskIntelligence
        try:
            assessment = CreditRiskIntelligence.assess_customer_risk(customer)
            return assessment['risk_score']
        except Exception:
            return 50  # Default medium risk if intelligence unavailable

    @staticmethod
    def _get_anomaly_count() -> int:
        """Get current anomaly count from FICL."""
        from core.services.anomaly_detection import AnomalyDetectionEngine
        try:
            report = AnomalyDetectionEngine.detect_all()
            return report['total_anomalies']
        except Exception:
            return 0

    @staticmethod
    def _get_cashflow_trend() -> str:
        """Determine cashflow trend direction."""
        from core.services.cashflow_observability import CashflowObservability
        try:
            summary = CashflowObservability.get_cashflow_summary(days=90)
            return summary.get('inflow_trend', 'STABLE')
        except Exception:
            return 'STABLE'

    @staticmethod
    def evaluate_customer(customer) -> PolicyDecision:
        """Evaluate policy rules for a customer.
        
        Returns a PolicyDecision with the most restrictive action.
        """
        from core.services.financial_truth_engine import FinancialTruthEngine

        safe_mode = FinancialPolicyEngine._check_ssot_conflict()
        triggered_rules = []
        explanations = []
        max_decision = 'ALLOW'
        risk_score = FinancialPolicyEngine._get_customer_risk_score(customer)

        # Derive balance
        derived_balance = FinancialTruthEngine.get_customer_balance(customer)
        overdue_balance = FinancialTruthEngine.get_customer_overdue_balance(customer)

        # RULE 1 — CREDIT SAFETY
        if customer.credit_limit > 0:
            utilization = derived_balance / customer.credit_limit if customer.credit_limit > 0 else Decimal('0')
            if utilization >= FinancialPolicyEngine.CREDIT_HARD_BLOCK_THRESHOLD:
                if not safe_mode:
                    max_decision = 'HARD_BLOCK'
                else:
                    max_decision = 'WARN'
                triggered_rules.append('CREDIT_SAFETY_95')
                explanations.append(
                    f'Credit utilization at {utilization * 100:.1f}% (threshold: 95%). '
                    f'Balance: {derived_balance}, Limit: {customer.credit_limit}.'
                )
            elif utilization >= FinancialPolicyEngine.CREDIT_WARN_THRESHOLD:
                if max_decision not in ('HARD_BLOCK', 'SOFT_BLOCK', 'ESCALATE_MANAGER'):
                    max_decision = 'WARN'
                triggered_rules.append('CREDIT_WARN_80')
                explanations.append(
                    f'Credit utilization at {utilization * 100:.1f}% (threshold: 80%).'
                )

        # RULE 2 — OVERDUE EXPOSURE
        if overdue_balance > Decimal('0.00'):
            # Find max overdue days
            from sales.models import SalesInvoice
            today = timezone.now().date()
            overdue_invoices = SalesInvoice.objects.filter(
                customer=customer,
                status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
                is_active=True,
                due_date__lt=today,
            )
            max_days = 0
            for inv in overdue_invoices:
                try:
                    days = (today - inv.due_date).days
                    max_days = max(max_days, days)
                except (TypeError, ValueError):
                    pass

            if max_days > FinancialPolicyEngine.OVERDUE_SOFT_BLOCK_DAYS:
                if max_decision not in ('HARD_BLOCK',):
                    max_decision = 'ESCALATE_MANAGER' if not safe_mode else 'WARN'
                triggered_rules.append('OVERDUE_90_DAYS')
                explanations.append(
                    f'Invoices overdue by {max_days} days (threshold: 90). '
                    f'Overdue balance: {overdue_balance}.'
                )
            elif max_days > FinancialPolicyEngine.OVERDUE_WARN_DAYS:
                if max_decision == 'ALLOW':
                    max_decision = 'WARN'
                triggered_rules.append('OVERDUE_30_DAYS')
                explanations.append(
                    f'Invoices overdue by {max_days} days (threshold: 30).'
                )

        # RULE 3 — CASHFLOW STABILITY
        cashflow_trend = FinancialPolicyEngine._get_cashflow_trend()
        if cashflow_trend == 'DECREASING':
            if max_decision == 'ALLOW':
                max_decision = 'WARN'
            triggered_rules.append('CASHFLOW_DECREASING')
            explanations.append('Cashflow trend is decreasing over the last 90 days.')

        # RULE 4 — ANOMALY PROTECTION
        anomaly_count = FinancialPolicyEngine._get_anomaly_count()
        if anomaly_count > FinancialPolicyEngine.ANOMALY_WARN_THRESHOLD:
            if max_decision == 'ALLOW':
                max_decision = 'WARN'
            triggered_rules.append('ANOMALY_THRESHOLD')
            explanations.append(
                f'{anomaly_count} anomalies detected (threshold: {FinancialPolicyEngine.ANOMALY_WARN_THRESHOLD}).'
            )

        # SSOT CONFLICT RULE
        if safe_mode:
            triggered_rules.append('SSOT_CONFLICT_SAFE_MODE')
            explanations.append('SSOT conflict detected — system in safe mode (read-only enforcement).')

        explanation = ' | '.join(explanations) if explanations else 'All policy rules passed.'

        return PolicyDecision(
            decision_type=max_decision,
            risk_score=risk_score,
            triggered_rules=triggered_rules,
            explanation=explanation,
            requires_review=max_decision in ('ESCALATE_MANAGER', 'SOFT_BLOCK'),
            safe_mode=safe_mode,
        )

    @staticmethod
    def evaluate_invoice_creation(customer, invoice_amount: Decimal) -> PolicyDecision:
        """Evaluate policy rules before creating a new invoice.
        
        Projects the impact of the new invoice on credit utilization.
        """
        from core.services.financial_truth_engine import FinancialTruthEngine

        safe_mode = FinancialPolicyEngine._check_ssot_conflict()
        triggered_rules = []
        explanations = []
        max_decision = 'ALLOW'
        risk_score = FinancialPolicyEngine._get_customer_risk_score(customer)

        # Project balance after invoice
        current_balance = FinancialTruthEngine.get_customer_balance(customer)
        projected_balance = current_balance + invoice_amount

        # RULE 1 — CREDIT SAFETY (projected)
        if customer.credit_limit > 0:
            projected_utilization = projected_balance / customer.credit_limit if customer.credit_limit > 0 else Decimal('0')
            if projected_utilization >= FinancialPolicyEngine.CREDIT_HARD_BLOCK_THRESHOLD:
                if not safe_mode:
                    max_decision = 'HARD_BLOCK'
                else:
                    max_decision = 'WARN'
                triggered_rules.append('CREDIT_SAFETY_PROJECTED')
                explanations.append(
                    f'Projected credit utilization: {projected_utilization * 100:.1f}% '
                    f'(current: {current_balance}, new invoice: {invoice_amount}, '
                    f'limit: {customer.credit_limit}).'
                )
            elif projected_utilization >= FinancialPolicyEngine.CREDIT_WARN_THRESHOLD:
                if max_decision not in ('HARD_BLOCK', 'SOFT_BLOCK', 'ESCALATE_MANAGER'):
                    max_decision = 'WARN'
                triggered_rules.append('CREDIT_WARN_PROJECTED')
                explanations.append(
                    f'Projected credit utilization will exceed 80%.'
                )

        # Customer BLOCKED status
        if customer.status == 'BLOCKED':
            max_decision = 'HARD_BLOCK'
            triggered_rules.append('CUSTOMER_BLOCKED')
            explanations.append('Customer status is BLOCKED.')

        # SSOT CONFLICT RULE
        if safe_mode:
            triggered_rules.append('SSOT_CONFLICT_SAFE_MODE')
            explanations.append('SSOT conflict detected — system in safe mode.')

        explanation = ' | '.join(explanations) if explanations else 'Invoice creation approved.'

        return PolicyDecision(
            decision_type=max_decision,
            risk_score=risk_score,
            triggered_rules=triggered_rules,
            explanation=explanation,
            requires_review=max_decision in ('ESCALATE_MANAGER', 'SOFT_BLOCK'),
            safe_mode=safe_mode,
        )

    @staticmethod
    def evaluate_payment(payment_amount: Decimal, remaining_balance: Decimal) -> PolicyDecision:
        """Evaluate policy rules for a payment.
        
        Prevents overpayment strictly.
        """
        triggered_rules = []
        explanations = []

        if payment_amount > remaining_balance:
            overpayment = payment_amount - remaining_balance
            return PolicyDecision(
                decision_type='SOFT_BLOCK',
                risk_score=70,
                triggered_rules=['OVERPAYMENT_PREVENTION'],
                explanation=f'Payment amount ({payment_amount}) exceeds remaining balance ({remaining_balance}). Overpayment: {overpayment}. Route to CREDIT_BALANCE ledger or reduce payment.',
                requires_review=True,
                safe_mode=False,
            )

        return PolicyDecision(
            decision_type='ALLOW',
            risk_score=0,
            triggered_rules=[],
            explanation='Payment within remaining balance.',
            requires_review=False,
            safe_mode=False,
        )

    @staticmethod
    def evaluate_system_health() -> PolicyDecision:
        """Evaluate overall system health for safe mode determination."""
        safe_mode = FinancialPolicyEngine._check_ssot_conflict()
        anomaly_count = FinancialPolicyEngine._get_anomaly_count()
        cashflow_trend = FinancialPolicyEngine._get_cashflow_trend()

        triggered_rules = []
        explanations = []
        max_decision = 'ALLOW'
        risk_score = 0

        if safe_mode:
            max_decision = 'WARN'
            risk_score = 80
            triggered_rules.append('SSOT_CONFLICT')
            explanations.append('SSOT conflict detected — system integrity at risk.')

        if anomaly_count > 10:
            if max_decision == 'ALLOW':
                max_decision = 'WARN'
            risk_score = max(risk_score, 60)
            triggered_rules.append('HIGH_ANOMALY_COUNT')
            explanations.append(f'{anomaly_count} anomalies detected.')

        if cashflow_trend == 'DECREASING':
            risk_score = max(risk_score, 40)
            triggered_rules.append('CASHFLOW_DECREASING')
            explanations.append('System-wide cashflow trend is decreasing.')

        explanation = ' | '.join(explanations) if explanations else 'System healthy.'

        return PolicyDecision(
            decision_type=max_decision,
            risk_score=risk_score,
            triggered_rules=triggered_rules,
            explanation=explanation,
            requires_review=safe_mode,
            safe_mode=safe_mode,
        )

    @staticmethod
    def log_decision(entity_type: str, entity_id: str, decision: PolicyDecision, user=None) -> 'DecisionRecord':
        """Log a policy decision to the DecisionRecord store.
        
        Automatically handles lifecycle: supersedes old decisions,
        enforces bounded storage.
        """
        from core.models.decision_record import DecisionRecord

        record = DecisionRecord.objects.create(
            entity_type=entity_type,
            entity_id=str(entity_id),
            risk_score=decision.risk_score,
            decision_type=decision.decision_type,
            triggered_rules=decision.triggered_rules,
            explanation=decision.explanation,
            source_modules=['FCUE', 'FICL', 'PolicyEngine'],
        )

        # Supersede older decisions for same entity
        DecisionRecord.supersede_decision(entity_type, str(entity_id), record.id)

        # Enforce bounded storage
        DecisionRecord.enforce_bounded_storage(max_records=200)

        # Expire old decisions
        DecisionRecord.expire_old_decisions(hours=24)

        return record

    @staticmethod
    def re_evaluate_all() -> dict:
        """Synchronous policy recomputation for all active customers.
        
        Returns summary of decisions. No background jobs.
        """
        from sales.models import Customer

        decisions = []
        for customer in Customer.objects.filter(status='ACTIVE')[:100]:
            decision = FinancialPolicyEngine.evaluate_customer(customer)
            record = FinancialPolicyEngine.log_decision(
                entity_type='Customer',
                entity_id=str(customer.pk),
                decision=decision,
            )
            decisions.append({
                'customer_id': str(customer.pk),
                'customer_name': customer.name,
                'decision_type': decision.decision_type,
                'risk_score': decision.risk_score,
                'record_id': str(record.id),
            })

        # System health
        system_decision = FinancialPolicyEngine.evaluate_system_health()
        FinancialPolicyEngine.log_decision(
            entity_type='System',
            entity_id='global',
            decision=system_decision,
        )

        return {
            'evaluated_count': len(decisions),
            'decisions': decisions,
            'system_decision': {
                'decision_type': system_decision.decision_type,
                'risk_score': system_decision.risk_score,
                'safe_mode': system_decision.safe_mode,
            },
            'timestamp': timezone.now().isoformat(),
        }

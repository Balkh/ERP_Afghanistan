"""Credit Risk Intelligence Extension — Advisory Risk Scoring.

Extends CreditPolicyEngine visibility with risk scoring, payment delay
patterns, utilization trends, and predictive signals.

Advisory only — does NOT modify CreditPolicyEngine enforcement.

Usage:
    risk = CreditRiskIntelligence.assess_customer_risk(customer)
    high_risk = CreditRiskIntelligence.get_high_risk_customers()
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone


class CreditRiskIntelligence:
    """Advisory credit risk scoring and predictive signals.
    
    All methods are read-only. Provides risk assessment, trend analysis,
    and predictive signals for human decision-making.
    """

    @staticmethod
    def _compute_payment_delay_score(customer) -> dict:
        """Analyze payment delay patterns for a customer.
        
        Returns delay statistics and a delay score (0-100, lower = worse).
        """
        from sales.models import SalesInvoice

        today = timezone.now().date()
        paid_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['PAID'],
            is_active=True,
            due_date__isnull=False,
        )

        if not paid_invoices.exists():
            return {
                'total_paid': 0,
                'on_time_count': 0,
                'late_count': 0,
                'avg_delay_days': 0,
                'max_delay_days': 0,
                'on_time_rate_pct': 0,
                'delay_score': 50,
            }

        total = paid_invoices.count()
        on_time = 0
        late = 0
        total_delay = 0
        max_delay = 0

        for inv in paid_invoices:
            try:
                delay = (inv.invoice_date - inv.due_date).days
            except (TypeError, ValueError):
                delay = 0

            if delay <= 0:
                on_time += 1
            else:
                late += 1
                total_delay += delay
                max_delay = max(max_delay, delay)

        avg_delay = total_delay / late if late > 0 else 0
        on_time_rate = (on_time / total * 100) if total > 0 else 0

        # Delay score: 100 = always on time, 0 = always very late
        delay_score = int(on_time_rate * 0.7 + max(0, 100 - avg_delay * 2) * 0.3)

        return {
            'total_paid': total,
            'on_time_count': on_time,
            'late_count': late,
            'avg_delay_days': round(avg_delay, 1),
            'max_delay_days': max_delay,
            'on_time_rate_pct': round(on_time_rate, 1),
            'delay_score': delay_score,
        }

    @staticmethod
    def _compute_utilization_trend(customer) -> dict:
        """Analyze credit utilization trend over time.
        
        Compares recent utilization (last 30 days) vs historical average.
        """
        from sales.models import SalesInvoice, CustomerPayment
        from core.services.financial_truth_engine import FinancialTruthEngine

        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        ninety_days_ago = today - timedelta(days=90)

        if customer.credit_limit <= 0:
            return {'trend': 'NO_LIMIT', 'recent_utilization': 0, 'historical_utilization': 0, 'direction': 'STABLE'}

        # Recent period (last 30 days)
        recent_invoices = SalesInvoice.objects.filter(
            customer=customer,
            invoice_date__gte=thirty_days_ago,
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        recent_payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__gte=thirty_days_ago,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        recent_net = recent_invoices - recent_payments
        recent_util = (recent_net / customer.credit_limit * 100) if customer.credit_limit > 0 else 0

        # Historical period (30-90 days ago)
        hist_invoices = SalesInvoice.objects.filter(
            customer=customer,
            invoice_date__gte=ninety_days_ago,
            invoice_date__lt=thirty_days_ago,
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        hist_payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__gte=ninety_days_ago,
            payment_date__lt=thirty_days_ago,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        hist_net = hist_invoices - hist_payments
        hist_util = (hist_net / customer.credit_limit * 100) if customer.credit_limit > 0 else 0

        # Direction
        diff = recent_util - hist_util
        if diff > 10:
            direction = 'INCREASING'
        elif diff < -10:
            direction = 'DECREASING'
        else:
            direction = 'STABLE'

        return {
            'trend': direction,
            'recent_utilization_pct': round(recent_util, 1),
            'historical_utilization_pct': round(hist_util, 1),
            'utilization_change_pct': round(diff, 1),
            'direction': direction,
        }

    @staticmethod
    def assess_customer_risk(customer) -> dict:
        """Full credit risk assessment for a customer.
        
        Returns:
            dict with risk_score (0-100), risk_level, contributing factors,
            payment delay analysis, utilization trend, and predictive signals.
        """
        from core.services.financial_truth_engine import FinancialTruthEngine

        balance = FinancialTruthEngine.get_customer_balance(customer)
        overdue = FinancialTruthEngine.get_customer_overdue_balance(customer)

        # Payment delay analysis
        delay = CreditRiskIntelligence._compute_payment_delay_score(customer)

        # Utilization trend
        utilization = CreditRiskIntelligence._compute_utilization_trend(customer)

        # Current utilization
        current_util = (balance / customer.credit_limit * 100) if customer.credit_limit > 0 else 0

        # Risk score computation (0-100, higher = riskier)
        risk_score = 0

        # Component 1: Current utilization (0-30 points)
        if current_util >= 100:
            risk_score += 30
        elif current_util >= 80:
            risk_score += 25
        elif current_util >= 60:
            risk_score += 15
        elif current_util >= 40:
            risk_score += 5

        # Component 2: Overdue balance (0-25 points)
        if overdue > Decimal('0.00'):
            overdue_ratio = overdue / balance if balance > 0 else Decimal('0')
            risk_score += min(int(overdue_ratio * 25), 25)

        # Component 3: Payment delay (0-25 points)
        delay_penalty = max(0, 25 - delay['delay_score'] // 4)
        risk_score += delay_penalty

        # Component 4: Utilization trend (0-20 points)
        if utilization['direction'] == 'INCREASING':
            risk_score += 15
        elif utilization['direction'] == 'STABLE':
            risk_score += 5

        # Risk level
        if risk_score >= 80:
            risk_level = 'CRITICAL'
        elif risk_score >= 60:
            risk_level = 'HIGH'
        elif risk_score >= 40:
            risk_level = 'MEDIUM'
        elif risk_score >= 20:
            risk_level = 'LOW'
        else:
            risk_level = 'MINIMAL'

        # Predictive signals
        signals = []
        if current_util >= 80 and utilization['direction'] == 'INCREASING':
            signals.append({
                'type': 'LIKELY_CREDIT_BREACH',
                'message': 'Customer likely to exceed credit limit within 30 days based on current trend.',
                'confidence': 'HIGH' if current_util >= 90 else 'MEDIUM',
            })
        if delay['on_time_rate_pct'] < 50 and overdue > Decimal('0.00'):
            signals.append({
                'type': 'HIGH_OVERDUE_RISK',
                'message': f'Customer has {delay["on_time_rate_pct"]}% on-time payment rate with {overdue} overdue.',
                'confidence': 'HIGH',
            })
        if utilization['direction'] == 'INCREASING' and delay['late_count'] > 3:
            signals.append({
                'type': 'DETERIORATING_PATTERN',
                'message': 'Increasing utilization combined with late payment history suggests deteriorating creditworthiness.',
                'confidence': 'MEDIUM',
            })

        return {
            'customer_id': str(customer.pk),
            'customer_name': customer.name,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'current_balance': str(balance),
            'overdue_balance': str(overdue),
            'current_utilization_pct': round(current_util, 1),
            'credit_limit': str(customer.credit_limit),
            'payment_delay': delay,
            'utilization_trend': utilization,
            'predictive_signals': signals,
            'assessment_date': timezone.now().date().isoformat(),
        }

    @staticmethod
    def get_high_risk_customers(threshold: int = 60) -> list:
        """Get all customers with risk score above threshold.
        
        Returns list of customer risk assessments sorted by risk_score descending.
        """
        from sales.models import Customer

        results = []
        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            assessment = CreditRiskIntelligence.assess_customer_risk(customer)
            if assessment['risk_score'] >= threshold:
                results.append(assessment)

        results.sort(key=lambda x: x['risk_score'], reverse=True)
        return results[:50]

    @staticmethod
    def predict_credit_breach(customer, days_ahead: int = 30) -> dict:
        """Predict if customer will exceed credit limit within N days.
        
        Uses linear extrapolation of recent invoice/payment velocity.
        """
        from sales.models import SalesInvoice, CustomerPayment
        from core.services.financial_truth_engine import FinancialTruthEngine

        if customer.credit_limit <= 0:
            return {'will_breach': False, 'reason': 'No credit limit set.'}

        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Recent velocity
        recent_invoices = SalesInvoice.objects.filter(
            customer=customer,
            invoice_date__gte=thirty_days_ago,
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        recent_payments = CustomerPayment.objects.filter(
            customer=customer,
            payment_date__gte=thirty_days_ago,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        daily_invoice_rate = recent_invoices / 30 if recent_invoices > 0 else Decimal('0.00')
        daily_payment_rate = recent_payments / 30 if recent_payments > 0 else Decimal('0.00')
        daily_net_increase = daily_invoice_rate - daily_payment_rate

        current_balance = FinancialTruthEngine.get_customer_balance(customer)
        projected_balance = current_balance + (daily_net_increase * days_ahead)
        will_breach = projected_balance > customer.credit_limit

        return {
            'customer_id': str(customer.pk),
            'customer_name': customer.name,
            'current_balance': str(current_balance),
            'credit_limit': str(customer.credit_limit),
            'daily_net_increase': str(daily_net_increase),
            'days_ahead': days_ahead,
            'projected_balance': str(projected_balance),
            'will_breach': will_breach,
            'breach_amount': str(projected_balance - customer.credit_limit) if will_breach else '0.00',
        }

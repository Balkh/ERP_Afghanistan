from typing import Dict, Any, List
from core.models.drift_prevention import DriftRecord, ModuleDriftState
from core.drift_prevention.gate import PreventionGate


class HealthReport:
    """Global system health report for drift prevention.

    Produces a 0–100 health score and determines readiness for Phase 3.
    """

    @staticmethod
    def generate() -> Dict[str, Any]:
        """Generate the system health report.

        Returns:
            Dict with:
            - health_score: int (0-100)
            - ready_for_phase_3: bool
            - module_count: int
            - blocked_modules: list
            - class a/b/c/d counts
            - critical_risks: list
            - module_details: list
        """
        modules = list(ModuleDriftState.objects.all())
        total_modules = len(modules)

        if total_modules == 0:
            return {
                'health_score': 100,
                'ready_for_phase_3': True,
                'module_count': 0,
                'blocked_modules': [],
                'class_a_count': 0,
                'class_b_count': 0,
                'class_c_count': 0,
                'class_d_count': 0,
                'critical_risks': [],
                'module_details': [],
                'note': 'No modules tracked yet — system is clean',
            }

        blocked_modules = PreventionGate.get_blocked_modules()
        class_a = sum(1 for m in modules if m.latest_classification == 'A')
        class_b = sum(1 for m in modules if m.latest_classification == 'B')
        class_c = sum(1 for m in modules if m.latest_classification == 'C')
        class_d = sum(1 for m in modules if m.latest_classification == 'D')

        total_c_d_count = sum(m.class_c_count + m.class_d_count for m in modules)
        total_comparisons = sum(m.total_comparisons for m in modules)

        health_score = HealthReport._calculate_health_score(
            total_modules=total_modules,
            blocked_count=len(blocked_modules),
            class_c_count=class_c,
            class_d_count=class_d,
            total_c_d_events=total_c_d_count,
            total_comparisons=total_comparisons,
        )

        critical_risks = []
        if blocked_modules:
            critical_risks.append(
                f'Module(s) BLOCKED: {", ".join(blocked_modules)}. '
                f'Cannot proceed to Phase 3 until cleared.'
            )
        if total_c_d_count > 0:
            critical_risks.append(
                f'{total_c_d_count} Critical/System drift event(s) detected across '
                f'{class_c + class_d} module(s). Requires investigation.'
            )
        if total_comparisons > 0 and total_c_d_count / total_comparisons > 0.1:
            critical_risks.append(
                f'High drift rate: {total_c_d_count}/{total_comparisons} '
                f'({total_c_d_count / total_comparisons * 100:.1f}%) comparisons resulted in '
                f'Critical/System drift.'
            )

        ready_for_phase_3 = len(blocked_modules) == 0 and total_c_d_count == 0

        module_details = []
        for m in modules:
            module_details.append({
                'module': m.module,
                'status': 'BLOCKED' if m.is_blocked else 'ALLOWED',
                'latest_classification': m.latest_classification,
                'total_comparisons': m.total_comparisons,
                'class_c_count': m.class_c_count,
                'class_d_count': m.class_d_count,
                'migration_allowed': not m.is_blocked,
            })

        return {
            'health_score': health_score,
            'ready_for_phase_3': ready_for_phase_3,
            'module_count': total_modules,
            'blocked_modules': blocked_modules,
            'class_a_count': class_a,
            'class_b_count': class_b,
            'class_c_count': class_c,
            'class_d_count': class_d,
            'total_critical_drifts': total_c_d_count,
            'total_comparisons': total_comparisons,
            'critical_risks': critical_risks,
            'module_details': module_details,
            'summary': HealthReport._generate_summary(
                health_score, ready_for_phase_3, blocked_modules, class_c, class_d
            ),
        }

    @staticmethod
    def _calculate_health_score(
        total_modules: int,
        blocked_count: int,
        class_c_count: int,
        class_d_count: int,
        total_c_d_events: int,
        total_comparisons: int,
    ) -> int:
        """Calculate a 0–100 health score based on drift state.

        Scoring:
        - Start at 100
        - -30 per blocked module
        - -20 per module with Class C as latest
        - -30 per module with Class D as latest
        - -5 per Class C event (up to -20)
        - -10 per Class D event (up to -30)
        """
        score = 100

        score -= blocked_count * 30
        score -= class_c_count * 20
        score -= class_d_count * 30
        score -= min(total_c_d_events * 5, 20)
        score -= min(total_c_d_events * 10, 30)

        return max(0, min(100, score))

    @staticmethod
    def _generate_summary(
        health_score: int,
        ready_for_phase_3: bool,
        blocked_modules: List[str],
        class_c_count: int,
        class_d_count: int,
    ) -> str:
        if ready_for_phase_3:
            return 'SYSTEM HEALTHY — All modules safe for Phase 3 migration.'
        if health_score >= 70:
            return (
                f'SYSTEM STABLE — {len(blocked_modules)} module(s) blocked. '
                f'Resolve before Phase 3.'
            )
        if health_score >= 40:
            return (
                f'SYSTEM DEGRADED — {class_c_count} module(s) with Critical drift, '
                f'{class_d_count} with System Failure. Immediate investigation required.'
            )
        return (
            f'SYSTEM CRITICAL — {class_c_count} Critical + {class_d_count} System failures. '
            f'Phase 3 is BLOCKED for all affected modules.'
        )

    @staticmethod
    def module_report(module: str) -> Dict[str, Any]:
        """Get detailed drift report for a single module."""
        state = PreventionGate.module_status(module)
        recent_records = DriftRecord.objects.filter(module=module).order_by('-created_at')[:20]
        class_c_records = DriftRecord.objects.filter(module=module, classification='C').order_by('-created_at')[:10]

        records_data = []
        for r in recent_records:
            records_data.append({
                'id': str(r.id),
                'operation': r.operation,
                'classification': r.classification,
                'financial_impact': r.financial_impact,
                'reference': r.reference,
                'engine_success': r.engine_success,
                'gateway_success': r.gateway_success,
                'mismatch_detail': r.mismatch_detail,
                'created_at': str(r.created_at),
            })

        return {
            'state': state,
            'recent_records': records_data,
            'critical_records_count': len(class_c_records),
            'total_records': DriftRecord.objects.filter(module=module).count(),
        }

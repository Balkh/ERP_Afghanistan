import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from core.models.drift_prevention import DriftRecord
from core.drift_prevention.registry import DriftRegistry

logger = logging.getLogger('erp.switchover.pattern')


class PatternDriftDetector:
    """Detects repeated mismatch patterns across drift records.

    If a pattern emerges (e.g., same account code mismatch in 3+ records),
    auto-blocks future executions of that pattern.

    Patterns detected:
        - account_mismatch — wrong account code in specific module
        - debit_mismatch — wrong debit amount
        - credit_mismatch — wrong credit amount
        - line_count_mismatch — wrong number of lines
        - gateway_failure — gateway consistently fails for a module
    """

    PATTERN_THRESHOLD = 3

    @staticmethod
    def analyze_module(module: str) -> Dict[str, Any]:
        class_c_records = DriftRecord.objects.filter(
            module=module,
            classification__in=['C', 'D'],
        ).order_by('-created_at')[:50]

        if not class_c_records.exists():
            return {'module': module, 'patterns': [], 'has_emerging_pattern': False, 'risk_level': 'LOW'}

        pattern_counts: Dict[str, int] = {}
        pattern_examples: Dict[str, List[str]] = {}

        for record in class_c_records:
            detail = record.mismatch_detail or {}
            comparison = detail.get('comparison', {})
            differences = comparison.get('differences', [])

            for diff in differences:
                diff_type = diff.get('type', 'unknown')
                field = diff.get('field', '')
                pattern_key = f'{diff_type}:{field}'

                if pattern_key not in pattern_counts:
                    pattern_counts[pattern_key] = 0
                    pattern_examples[pattern_key] = []

                pattern_counts[pattern_key] += 1
                if len(pattern_examples[pattern_key]) < 3:
                    pattern_examples[pattern_key].append(
                        f'ref={record.reference}: engine={diff.get("engine")} vs gateway={diff.get("gateway")}'
                    )

        emerging_patterns = []
        has_emerging = False
        total_events = class_c_records.count()

        for pattern_key, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
            if count >= PatternDriftDetector.PATTERN_THRESHOLD:
                has_emerging = True
                emerging_patterns.append({
                    'pattern': pattern_key,
                    'occurrences': count,
                    'frequency': f'{count}/{total_events} ({count / total_events * 100:.0f}%)',
                    'examples': pattern_examples.get(pattern_key, [])[:2],
                })

        risk_level = 'HIGH' if has_emerging else ('MEDIUM' if pattern_counts else 'LOW')

        return {
            'module': module,
            'patterns': emerging_patterns,
            'has_emerging_pattern': has_emerging,
            'risk_level': risk_level,
            'total_c_d_events': total_events,
            'unique_pattern_types': len(pattern_counts),
        }

    @staticmethod
    def should_block_module(module: str) -> bool:
        analysis = PatternDriftDetector.analyze_module(module)
        if analysis['has_emerging_pattern']:
            logger.warning(
                f'[PATTERN_DRIFT] Module {module} has {len(analysis["patterns"])} '
                f'emerging patterns — auto-blocking.'
            )
            return True
        return False

    @staticmethod
    def all_modules_risk() -> List[Dict[str, Any]]:
        modules = list(DriftRecord.objects.values_list('module', flat=True).distinct())
        return [PatternDriftDetector.analyze_module(m) for m in modules]

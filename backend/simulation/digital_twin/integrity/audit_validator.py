from typing import List, Dict, Optional


class AuditValidator:
    def __init__(self):
        pass

    def check_causal_traceability(self, events: List[Dict]) -> Dict:
        try:
            event_ids = {e.get('event_id') for e in events}
            missing_parents = []
            for event in events:
                parent = event.get('causal_parent')
                if parent is not None and parent not in event_ids:
                    missing_parents.append(
                        f"Event {event.get('event_id')} references missing parent {parent}"
                    )
            passed = len(missing_parents) == 0
            return {
                'passed': passed,
                'missing_parents': missing_parents,
                'count': len(missing_parents),
            }
        except Exception as e:
            return {
                'passed': False,
                'missing_parents': [],
                'count': 0,
                'details': f'Error checking causal traceability: {e}',
            }

    def check_completeness(self, events: List[Dict]) -> Dict:
        try:
            gaps = []
            sorted_events = sorted(events, key=lambda e: e.get('tick', 0))
            if not sorted_events:
                return {'passed': True, 'gaps': []}

            expected_types = {e.get('type') for e in events}
            for i in range(1, len(sorted_events)):
                prev_tick = sorted_events[i - 1].get('tick', 0)
                curr_tick = sorted_events[i].get('tick', 0)
                if curr_tick - prev_tick > 1:
                    for gap_tick in range(prev_tick + 1, curr_tick):
                        gaps.append(f"Missing tick {gap_tick}")
            passed = len(gaps) == 0
            return {
                'passed': passed,
                'gaps': gaps,
            }
        except Exception as e:
            return {
                'passed': False,
                'gaps': [],
                'details': f'Error checking completeness: {e}',
            }

    def check_chronological(self, events: List[Dict]) -> Dict:
        try:
            out_of_order = 0
            for i in range(1, len(events)):
                if events[i].get('tick', 0) < events[i - 1].get('tick', 0):
                    out_of_order += 1
            passed = out_of_order == 0
            return {
                'passed': passed,
                'out_of_order': out_of_order,
            }
        except Exception as e:
            return {
                'passed': False,
                'out_of_order': 0,
                'details': f'Error checking chronological order: {e}',
            }

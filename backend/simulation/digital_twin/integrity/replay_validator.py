from typing import List, Dict, Optional


class ReplayValidator:
    def __init__(self):
        pass

    def check_determinism(
        self, original_events: List[Dict], replay_events: List[Dict]
    ) -> Dict:
        try:
            total_original = len(original_events)
            total_replay = len(replay_events)
            mismatches = []
            max_len = min(total_original, total_replay)
            for i in range(max_len):
                o = original_events[i]
                r = replay_events[i]
                if o.get('event_id') != r.get('event_id'):
                    mismatches.append({
                        'index': i,
                        'field': 'event_id',
                        'expected': o.get('event_id'),
                        'actual': r.get('event_id'),
                    })
                elif o.get('type') != r.get('type'):
                    mismatches.append({
                        'index': i,
                        'field': 'type',
                        'expected': o.get('type'),
                        'actual': r.get('type'),
                    })
                elif o.get('tick') != r.get('tick'):
                    mismatches.append({
                        'index': i,
                        'field': 'tick',
                        'expected': o.get('tick'),
                        'actual': r.get('tick'),
                    })
                elif o.get('payload') != r.get('payload'):
                    mismatches.append({
                        'index': i,
                        'field': 'payload',
                        'expected': o.get('payload'),
                        'actual': r.get('payload'),
                    })

            if total_original != total_replay:
                mismatches.append({
                    'index': -1,
                    'field': 'length',
                    'expected': total_original,
                    'actual': total_replay,
                })

            match_count = max_len - len(
                [m for m in mismatches if m.get('index') != -1]
            )
            total_possible = max(total_original, total_replay)
            match_percentage = (
                round((match_count / total_possible) * 100, 2)
                if total_possible > 0
                else 100.0
            )
            passed = len(mismatches) == 0 and total_original == total_replay
            return {
                'passed': passed,
                'match_percentage': match_percentage,
                'mismatches': mismatches,
                'total_original': total_original,
                'total_replay': total_replay,
            }
        except Exception as e:
            return {
                'passed': False,
                'match_percentage': 0.0,
                'mismatches': [],
                'total_original': len(original_events),
                'total_replay': len(replay_events),
                'details': f'Error checking determinism: {e}',
            }

    def check_hashes(self, original_hashes: Dict, replay_hashes: Dict) -> Dict:
        try:
            matching = 0
            divergent = 0
            all_keys = set(original_hashes.keys()) | set(replay_hashes.keys())
            for key in all_keys:
                o = original_hashes.get(key)
                r = replay_hashes.get(key)
                if o == r:
                    matching += 1
                else:
                    divergent += 1
            passed = divergent == 0
            return {
                'passed': passed,
                'matching': matching,
                'divergent': divergent,
            }
        except Exception as e:
            return {
                'passed': False,
                'matching': 0,
                'divergent': 0,
                'details': f'Error checking hashes: {e}',
            }

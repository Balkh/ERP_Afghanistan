from typing import List, Dict, Set


class InventoryValidator:
    def __init__(self):
        pass

    def check_no_negative(self, batches: List[Dict]) -> Dict:
        try:
            negative_batches = []
            for batch in batches:
                qty = batch.get('remaining_quantity', 0)
                if qty < 0:
                    negative_batches.append(batch.get('batch_id', 'unknown'))
            passed = len(negative_batches) == 0
            return {
                'passed': passed,
                'negative_batches': negative_batches,
                'count': len(negative_batches),
            }
        except Exception as e:
            return {
                'passed': False,
                'negative_batches': [],
                'count': 0,
                'details': f'Error checking negative quantities: {e}',
            }

    def check_fifo(self, movements: List[Dict]) -> Dict:
        try:
            batch_movements: Dict[str, List[Dict]] = {}
            for m in movements:
                bid = m.get('batch_id', 'unknown')
                batch_movements.setdefault(bid, []).append(m)

            fifo_violations = []
            for bid, moves in batch_movements.items():
                moves_sorted = sorted(moves, key=lambda x: x.get('tick', 0))
                running = 0.0
                for m in moves_sorted:
                    qty = m.get('quantity', 0.0)
                    direction = m.get('direction', '')
                    if direction == 'IN':
                        running += qty
                    elif direction == 'OUT':
                        running -= qty
                        if running < 0:
                            fifo_violations.append(
                                f"Batch {bid}: OUT of {qty} at tick {m.get('tick', 0)} "
                                f"exceeds available {running + qty}"
                            )

            passed = len(fifo_violations) == 0
            return {
                'passed': passed,
                'fifo_violations': fifo_violations,
                'count': len(fifo_violations),
            }
        except Exception as e:
            return {
                'passed': False,
                'fifo_violations': [],
                'count': 0,
                'details': f'Error checking FIFO: {e}',
            }

    def check_batch_integrity(self, batches: List[Dict]) -> Dict:
        try:
            corrupted_batches = []
            issues = []
            required_fields = {'batch_id', 'remaining_quantity'}
            for batch in batches:
                bid = batch.get('batch_id', 'unknown')
                missing = required_fields - set(batch.keys())
                if missing:
                    corrupted_batches.append(bid)
                    issues.append(f"Batch {bid} missing fields: {missing}")
                qty = batch.get('remaining_quantity')
                if qty is not None and qty < 0:
                    corrupted_batches.append(bid)
                    issues.append(f"Batch {bid} has negative remaining quantity: {qty}")
            passed = len(corrupted_batches) == 0
            return {
                'passed': passed,
                'corrupted_batches': corrupted_batches,
                'issues': issues,
            }
        except Exception as e:
            return {
                'passed': False,
                'corrupted_batches': [],
                'issues': [f'Error checking batch integrity: {e}'],
            }

"""
Task D: LayerIsolationValidator — validates strict layer separation.
"""
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.audit.dependencies.validator')


class LayerIsolationValidator:
    LAYER_BOUNDARIES = {
        'simulation.agents': ['simulation.agents', 'simulation.clocks',
                               'simulation.events', 'simulation.metrics',
                               'simulation.scheduler', 'simulation.context'],
        'simulation.workflows': ['simulation.workflows', 'simulation.events'],
        'simulation.truth_engine': ['simulation.truth_engine', 'simulation.events',
                                     'simulation.clocks'],
        'simulation.audit': ['simulation.audit', 'simulation.events',
                              'simulation.truth_engine'],
    }

    def validate(self, simulation_path: str) -> Dict[str, Any]:
        violations = []
        for root, dirs, files in os.walk(simulation_path):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, simulation_path)
                file_layer = self._classify_file(rel_path)
                if not file_layer:
                    continue
                allowed = self.LAYER_BOUNDARIES.get(file_layer, [])
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    stripped = line.strip()
                    if not stripped.startswith(('import ', 'from ')):
                        continue
                    imported = self._extract_import_target(stripped)
                    if imported and imported.startswith('simulation.'):
                        imported_layer = imported.rsplit('.', 1)[0]
                        if imported_layer not in allowed and \
                           imported_layer != file_layer and \
                           not imported_layer.startswith(file_layer):
                            violations.append({
                                'file': rel_path,
                                'import': imported,
                                'from_layer': file_layer,
                                'to_layer': imported_layer,
                            })
        return {
            'layer_violations': violations,
            'violation_count': len(violations),
            'layers_isolated': len(violations) == 0,
        }

    def _classify_file(self, rel_path: str) -> str:
        norm = rel_path.replace(os.sep, '.')
        for layer in sorted(self.LAYER_BOUNDARIES.keys(), reverse=True):
            if norm.startswith(layer):
                return layer
        return ''

    def _extract_import_target(self, line: str) -> str:
        if line.startswith('import '):
            return line.split('import ', 1)[1].split(' as ')[0].split(',')[0].strip()
        if line.startswith('from '):
            return line.split('from ', 1)[1].split(' import ', 1)[0].strip()
        return ''

"""
Task D: DependencyAnalyzer — detects circular imports, illegal ERP imports, coupling.
"""
import logging
import os
from typing import Any, Dict, List, Set

logger = logging.getLogger('erp.simulation.audit.dependencies.analyzer')


class DependencyAnalyzer:
    FORBIDDEN_PRODUCTION_PATHS = [
        'accounting', 'sales', 'purchases', 'inventory', 'payments',
        'payroll', 'hr', 'backup', 'core', 'security',
    ]
    ALLOWED_BRIDGE_FILES = [
        'truth_engine/collector/actual.py',
    ]

    def analyze(self, simulation_path: str) -> Dict[str, Any]:
        violations = []
        domain_imports = []
        circular_risks = []
        for root, dirs, files in os.walk(simulation_path):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(fpath, simulation_path)
                imports = self._extract_imports(content)
                if rel_path.replace(os.sep, '/') in self.ALLOWED_BRIDGE_FILES:
                    continue
                for imp in imports:
                    for prod in self.FORBIDDEN_PRODUCTION_PATHS:
                        if imp.startswith(prod):
                            violations.append({
                                'file': rel_path,
                                'import': imp,
                                'type': 'production_import',
                            })
                    if imp.startswith('simulation.') and rel_path.replace(os.sep, '.')[:-3] != imp:
                        parts = imp.split('.')
                        file_parts = rel_path.replace(os.sep, '.').replace('.py', '').split('.')
                        common = len(set(parts) & set(file_parts))
                        if common <= 1 and len(parts) > 2:
                            circular_risks.append({
                                'file': rel_path,
                                'import': imp,
                                'type': 'cross_layer',
                            })
        return {
            'total_files_scanned': self._count_py_files(simulation_path),
            'production_import_violations': violations,
            'production_violation_count': len(violations),
            'cross_layer_imports': circular_risks,
            'cross_layer_count': len(circular_risks),
            'has_production_coupling': len(violations) > 0,
        }

    def _extract_imports(self, content: str) -> List[str]:
        imports = []
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('import '):
                parts = stripped.split('import ', 1)[1].split(',')
                for p in parts:
                    imports.append(p.strip().split(' as ')[0].split('.')[0])
            elif stripped.startswith('from '):
                parts = stripped.split('from ', 1)[1].split(' import ', 1)[0]
                imports.append(parts.strip().split('.')[0])
        return imports

    def _count_py_files(self, path: str) -> int:
        count = 0
        for root, dirs, files in os.walk(path):
            count += sum(1 for f in files if f.endswith('.py'))
        return count

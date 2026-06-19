import os
import re
import ast
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

base = Path('.')

# Get all the django apps
apps = []
exclude_dirs = {'__pycache__', 'scripts', 'staticfiles', 'htmlcov', 'logs', 'tests', 'archive'}
for item in base.iterdir():
    if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
        if (item / '__init__.py').exists() or (item / 'apps.py').exists():
            if item.name not in exclude_dirs:
                apps.append(item.name)

# Analyze each app
print("=" * 100)
print("APP ANALYSIS")
print("=" * 100)
for app in sorted(apps):
    app_path = base / app
    if not app_path.is_dir():
        continue

    py_files = [f for f in app_path.rglob('*.py') if '__pycache__' not in str(f)]
    total_files = len(py_files)
    total_lines = 0
    for f in py_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                total_lines += sum(1 for _ in fp)
        except:
            pass

    # Models - collect class names
    models = []
    models_file = app_path / 'models.py'
    if models_file.exists():
        try:
            tree = ast.parse(models_file.read_text(encoding='utf-8', errors='ignore'))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = [ast.unparse(b) for b in node.bases]
                    if 'Model' in str(bases) or any('Model' in b for b in bases):
                        # Get first line of docstring if any
                        doc = ast.get_docstring(node)
                        purpose = doc.split('\n')[0][:80] if doc else ''
                        models.append((node.name, purpose))
        except:
            pass

    models_dir = app_path / 'models'
    if models_dir.exists():
        for mf in models_dir.glob('*.py'):
            if mf.name == '__init__.py':
                continue
            try:
                tree = ast.parse(mf.read_text(encoding='utf-8', errors='ignore'))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        bases = [ast.unparse(b) for b in node.bases]
                        if 'Model' in str(bases) or any('Model' in b for b in bases):
                            doc = ast.get_docstring(node)
                            purpose = doc.split('\n')[0][:80] if doc else ''
                            models.append((f"{node.name} ({mf.name})", purpose))
            except:
                pass

    print(f"\n{app}: {total_files} files, {total_lines} lines, {len(models)} models")
    for name, purpose in models:
        print(f"  MODEL {name} | {purpose}")

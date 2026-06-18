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


def safe_read(p):
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
            return fp.read()
    except:
        return ''


def line_count(p):
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
            return sum(1 for _ in fp)
    except:
        return 0


def collect_classes_in_file(path, base_class_substrings=()):
    """Collect class definitions matching base classes"""
    src = safe_read(path)
    try:
        tree = ast.parse(src)
    except:
        return []
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except:
                    bases.append('')
            for bc in base_class_substrings:
                if any(bc in b for b in bases):
                    doc = ast.get_docstring(node)
                    purpose = doc.split('\n')[0][:90] if doc else ''
                    result.append((node.name, purpose, bases))
                    break
    return result


def collect_top_functions(path):
    """Collect top-level function and class definitions"""
    src = safe_read(path)
    try:
        tree = ast.parse(src)
    except:
        return []
    result = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            purpose = doc.split('\n')[0][:90] if doc else ''
            result.append(('class', node.name, purpose))
        elif isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            purpose = doc.split('\n')[0][:90] if doc else ''
            result.append(('def', node.name, purpose))
    return result


# Analyze each app
print("=" * 100)
print("COMPREHENSIVE APP ANALYSIS")
print("=" * 100)

for app in sorted(apps):
    app_path = base / app
    if not app_path.is_dir():
        continue

    print(f"\n{'#' * 100}")
    print(f"# APP: {app}")
    print(f"{'#' * 100}")

    py_files = [f for f in app_path.rglob('*.py') if '__pycache__' not in str(f)]
    total_files = len(py_files)
    total_lines = sum(line_count(f) for f in py_files)

    print(f"\nFiles: {total_files}, Lines: {total_lines}")

    # Files summary
    print(f"\n--- File Summary ---")
    for f in sorted(py_files):
        rel = f.relative_to(app_path)
        print(f"  {line_count(f):5d}  {rel}")

    # Models
    print(f"\n--- MODELS ---")
    models = []
    models_file = app_path / 'models.py'
    if models_file.exists():
        for name, purpose, bases in collect_classes_in_file(models_file, ('Model',)):
            models.append((name, purpose))
    models_dir = app_path / 'models'
    if models_dir.exists():
        for mf in sorted(models_dir.glob('*.py')):
            if mf.name == '__init__.py':
                continue
            for name, purpose, bases in collect_classes_in_file(mf, ('Model',)):
                models.append((f"{name} ({mf.name})", purpose))
    for name, purpose in models:
        print(f"  - {name} | {purpose}")

    # Serializers
    print(f"\n--- SERIALIZERS ---")
    serializers = []
    for f in py_files:
        if 'serial' in f.name.lower():
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'class' and 'Serializer' in name:
                    serializers.append((f"{name} ({f.name})", purpose))
    if not serializers:
        for f in py_files:
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'class' and 'Serializer' in name:
                    serializers.append((f"{name} ({f.name})", purpose))
    for name, purpose in serializers:
        print(f"  - {name} | {purpose}")

    # Views
    print(f"\n--- VIEWS / VIEWSETS ---")
    views = []
    for f in py_files:
        if 'view' in f.name.lower():
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'class' and ('View' in name or 'ViewSet' in name):
                    views.append((f"{name} ({f.name})", purpose))
    if not views:
        for f in py_files:
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'class' and ('View' in name or 'ViewSet' in name):
                    views.append((f"{name} ({f.name})", purpose))
    for name, purpose in views:
        print(f"  - {name} | {purpose}")

    # Services
    print(f"\n--- SERVICES ---")
    services_dir = app_path / 'services'
    if services_dir.exists():
        for sf in sorted(services_dir.glob('*.py')):
            if sf.name == '__init__.py':
                continue
            for kind, name, purpose in collect_top_functions(sf):
                if kind == 'class':
                    print(f"  - CLASS {name} ({sf.name}) | {purpose}")
                else:
                    print(f"  - DEF {name} ({sf.name}) | {purpose}")

    # Signals
    print(f"\n--- SIGNALS ---")
    signals = []
    for f in py_files:
        if 'signal' in f.name.lower():
            src = safe_read(f)
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'def' and ('receiver' in name.lower() or 'signal' in name.lower()):
                    signals.append((f"{name} ({f.name})", purpose))
    if not signals:
        for f in py_files:
            for kind, name, purpose in collect_top_functions(f):
                if kind == 'def' and 'receiver' in name.lower():
                    signals.append((f"{name} ({f.name})", purpose))
    for name, purpose in signals:
        print(f"  - {name} | {purpose}")

    # Permissions
    print(f"\n--- PERMISSIONS ---")
    perms = []
    for f in py_files:
        for kind, name, purpose in collect_top_functions(f):
            if kind == 'class' and 'Permission' in name:
                perms.append((f"{name} ({f.name})", purpose))
    for name, purpose in perms:
        print(f"  - {name} | {purpose}")

    # Middleware
    print(f"\n--- MIDDLEWARE ---")
    for f in py_files:
        for kind, name, purpose in collect_top_functions(f):
            if kind == 'class' and 'Middleware' in name:
                print(f"  - {name} ({f.name}) | {purpose}")

    # URLs
    print(f"\n--- URL ROUTES ---")
    urls_file = app_path / 'urls.py'
    if urls_file.exists():
        src = safe_read(urls_file)
        # Find all path() and re_path() calls
        for match in re.finditer(r"(?:path|re_path|include)\s*\(\s*['\"]([^'\"]*)['\"](?:[^,]*?,\s*([\w\.]+))?", src):
            route = match.group(1)
            view = match.group(2) or ''
            print(f"  {route:50s} -> {view}")

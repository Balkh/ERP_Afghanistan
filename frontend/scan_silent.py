import glob
import ast

risky = []
for f in glob.glob('ui/**/*.py', recursive=True):
    if '__pycache__' in f or 'test' in f.lower():
        continue
    try:
        tree = ast.parse(open(f, encoding='utf-8').read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    risky.append((f, node.lineno, 'empty except'))
                elif len(node.body) == 0:
                    risky.append((f, node.lineno, 'empty block'))
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call):
                    call = node.body[0].value
                    if hasattr(call.func, 'attr') and call.func.attr in ('pass', 'print'):
                        risky.append((f, node.lineno, 'logging only'))
                if node.type is None:
                    risky.append((f, node.lineno, 'bare except'))
    except Exception:
        pass

for r in risky:
    print(f'{r[0]}:{r[1]} - {r[2]}')
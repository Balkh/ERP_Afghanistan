import glob
import re

patterns = [
    (r'setStyleSheet\([\'\"].*#[0-9a-fA-F]{3,8}', 'hardcoded hex color'),
    (r'setStyleSheet\([\'\"].*\b\d+px', 'hardcoded px in setStyleSheet'),
    (r'setStyleSheet\([\'\"].*\b\d+(?:\.\d+)?(?:em|rem|%)', 'hardcoded font-size'),
    (r'QColor\(#', 'QColor hex'),
    (r'QColor\([\'"]#[0-9a-fA-F]{3,8}', 'QColor with hex'),
]

results = {}
for f in glob.glob('ui/**/*.py', recursive=True):
    if '__pycache__' in f or 'test' in f.lower():
        continue
    content = open(f, encoding='utf-8').read()
    for pattern, desc in patterns:
        matches = re.findall(pattern, content)
        if matches:
            if f not in results:
                results[f] = {}
            results[f][desc] = results[f].get(desc, 0) + len(matches)

for f, counts in sorted(results.items(), key=lambda x: -sum(x[1].values())):
    print(f'{f}:')
    for desc, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f'  {desc}: {count}')
import glob
import re

patterns = [
    (r'setStyleSheet\([\'"].*#[0-9a-fA-F]{3,8}', 'hardcoded hex color'),
    (r'setStyleSheet\([\'"].*\b\d+px', 'hardcoded px'),
    (r'QTableWidget\(', 'QTableWidget usage'),
    (r'get_endpoint\([\'"]', 'hardcoded endpoint'),
    (r'api_client\.(get|post|put|delete)\(', 'direct api_client call'),
    (r'QPushButton\(', 'QPushButton usage'),
    (r'QMessageBox\.', 'QMessageBox usage'),
    (r'QDialog\(', 'QDialog usage'),
]

for f in glob.glob('ui/**/*.py', recursive=True):
    if '__pycache__' in f or 'test' in f.lower():
        continue
    content = open(f, encoding='utf-8').read()
    for pattern, desc in patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f'{f}: {len(matches)} {desc}')
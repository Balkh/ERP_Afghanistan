import glob
import re

for f in glob.glob('ui/**/*.py', recursive=True):
    if '__pycache__' in f or 'test' in f.lower():
        continue
    content = open(f, encoding='utf-8').read()
    matches = re.findall(r'setStyleSheet\([\'\"].*?\)', content)
    hardcoded = 0
    for s in re.findall(r'setStyleSheet\([\'\"].*?\)', content):
        if re.search(r'#[0-9a-fA-F]{3,8}', s) or re.search(r'\b\d+px', s):
            print(f'{f}: {s[:150]}')
            break
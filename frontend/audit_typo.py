import re, os, sys
sys.path.insert(0, '.')

def audit_typography(filepath):
    issues = []
    try:
        src = open(filepath, encoding='utf-8').read()
    except:
        return issues
    try:
        compile(src, filepath, 'exec')
    except SyntaxError:
        return issues

    lines = src.split('\n')
    
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('#') or s.startswith('"""'):
            continue

        # 1. Very small fonts (< 9pt)
        m = re.search(r'setFont\(QFont\([^,]+,\s*(\d+)', s)
        if m and int(m.group(1)) <= 8:
            issues.append(f'TINY FONT ({m.group(1)}pt): line {i}: {s[:70]}')

        # 2. COLOR_STATUS_* used as text color (these are pastel/light)
        for status in ['COLOR_STATUS_VALID', 'COLOR_STATUS_INVALID', 'COLOR_STATUS_WARNING', 'COLOR_STATUS_PENDING']:
            if status in s and ('color:' in s or 'setForeground' in s or 'setPen' in s or 'color =' in s):
                # Check if it's used as actual text color (not background)
                if 'background' not in s.lower():
                    issues.append(f'PASTEL TEXT: line {i}: {status} used as text color - may be unreadable')

        # 3. COLOR_TEXT_MUTED on important labels (muted = very light gray #9ca3af)
        if 'COLOR_TEXT_MUTED' in s and 'title' in s.lower():
            issues.append(f'MUTED TITLE: line {i}: Title uses COLOR_TEXT_MUTED - low contrast')

        # 4. Check for missing font weight on headers
        if 'QLabel' in s and 'header' in s.lower():
            # Look ahead for setFont
            blk = '\n'.join(lines[i:min(i+5, len(lines))])
            if 'setFont' not in blk and 'font-weight' not in blk:
                issues.append(f'NO FONT WEIGHT: line {i}: Header QLabel without font-weight')

    return issues

ui_dir = 'ui'
skipped = {'__pycache__', 'scripts', 'tests', 'theme'}
for root, dirs, files in os.walk(ui_dir):
    dirs[:] = [d for d in dirs if d not in skipped]
    for f in sorted(files):
        if not f.endswith('.py'):
            continue
        fp = os.path.join(root, f)
        issues = audit_typography(fp)
        if issues:
            print(f'=== {fp} ===')
            for i in issues:
                print(f'  {i}')

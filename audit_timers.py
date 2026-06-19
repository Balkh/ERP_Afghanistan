import re
import os

files = [
    'frontend/ui/main_window.py',
    'frontend/ui/accounting/report_browser.py',
    'frontend/ui/common/product_selection_dialog.py',
    'frontend/ui/system/licensing_screen.py',
]

for f in files:
    if not os.path.exists(f):
        print(f'{f}: NOT FOUND')
        continue
    with open(f, 'rb') as fh:
        raw = fh.read()
    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        content = raw.decode('latin-1', errors='replace')

    starts = re.findall(r'\.start\s*\(', content)
    stops = re.findall(r'\.stop\s*\(', content)
    timer_lines = [line.strip() for line in content.split('\n') if 'QTimer' in line or '.start(' in line or '.stop(' in line][:30]
    print(f'\n=== {f} ===')
    print(f'  starts: {len(starts)}')
    print(f'  stops: {len(stops)}')
    print(f'  balance: {len(starts) - len(stops)}')
    print('  relevant lines:')
    for line in timer_lines:
        print(f'    {line[:120]}')

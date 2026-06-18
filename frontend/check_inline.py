import re

content = open('ui/sales/sales_invoice_screen.py', encoding='utf-8').read()
matches = re.findall(r'setStyleSheet\([\'\"].*?\)', content)
print(f'Total setStyleSheet calls: {len(matches)}')
for s in matches[:5]:
    print(s[:200])
    print('---')
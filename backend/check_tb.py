import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, '.')
django.setup()
import requests
r = requests.get('http://localhost:8000/api/accounting/accounts/trial_balance/', params={'as_of_date': '2026-05-14'}, timeout=5)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    d = r.json()
    if 'data' in d:
        d = d['data']
    print(f'Accounts count: {len(d.get("accounts", []))}')
    print(f'Total debit: {d.get("total_debit")}')
else:
    print(r.text[:300])

import django, os, sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name=%s)', ['common_auditlog'])
    exists = cursor.fetchone()[0]
    if exists:
        cursor.execute('SELECT COUNT(*) FROM common_auditlog')
        count = cursor.fetchone()[0]
        print(f'table common_auditlog exists with {count} rows')
    else:
        print('table common_auditlog does not exist')

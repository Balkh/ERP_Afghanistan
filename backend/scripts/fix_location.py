"""Fix remaining Batch location= -> warehouse= in test files."""
import os, re, glob

test_dir = r'E:\all downloads\Pharmacy_ERP\backend\tests'
files = glob.glob(os.path.join(test_dir, '*.py'))
count = 0

for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'location=' not in content:
        continue
    # Skip if no Batch-related code
    if 'Batch(' not in content and 'Batch.objects.create(' not in content:
        continue

    original = content
    # Replace location=<any_value> with warehouse=None (broader pattern)
    content = re.sub(r'\blocation=[^,\)]+', 'warehouse=None', content)

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        count += 1
        print(f'Fixed: {os.path.basename(fpath)}')

print(f'Total fixed: {count}')

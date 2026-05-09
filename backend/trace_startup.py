"""Trace Django startup."""
import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

print("Starting...", flush=True)

try:
    import django
    print("Imported django", flush=True)
    
    print("Calling setup()...", flush=True)
    django.setup()
    print("Django setup done!", flush=True)
    
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    traceback.print_exc()
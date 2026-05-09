"""
Pharmacy ERP Executable Startup Process
Handles initialization, path setup, and application startup for packaged deployment
"""
import sys
import os
import logging
from pathlib import Path


def setup_environment():
    """
    Setup the environment for the packaged application
    """
    # Get the base directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add backend to Python path
    backend_path = os.path.join(base_dir, 'backend')
    if os.path.exists(backend_path):
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
    
    # Set environment variables for Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Create necessary directories
    create_app_directories(base_dir)
    
    return base_dir


def create_app_directories(base_dir):
    """
    Create all necessary application directories
    """
    from config.production_config import get_data_path, get_log_path, get_config_path, get_backup_path
    
    directories = [
        get_data_path(),
        get_log_path(),
        get_config_path(),
        get_backup_path(),
        os.path.join(get_data_path(), 'media'),
        os.path.join(get_data_path(), 'static'),
        os.path.join(get_data_path(), 'temp'),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def initialize_django():
    """
    Initialize Django for the packaged application
    """
    import django
    from django.conf import settings
    
    # Configure Django settings for production
    if not settings.configured:
        settings.configure(
            DEBUG=False,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': os.path.join(get_data_path(), 'pharmacy_erp.db'),
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'rest_framework',
                'corsheaders',
                'common',
                'core',
                'inventory',
                'sales',
                'purchases',
                'accounting',
                'payments',
                'licensing',
                'reports',
                'security',
            ],
            # ... other settings would be loaded from config file
        )
    
    django.setup()


def run_database_migrations():
    """
    Run any pending database migrations
    """
    try:
        from django.core.management import call_command
        from django.db import connection
        from django.db.utils import OperationalError
        
        # Check if database is accessible
        try:
            connection.ensure_connection()
        except OperationalError:
            # Database might not exist yet, create it
            from config.production_config import get_database_path
            db_path = get_database_path()
            if not os.path.exists(db_path):
                # Create empty database file
                open(db_path, 'a').close()
        
        # Run migrations
        call_command('migrate', verbosity=0)
        
        # Seed default data if needed
        seed_default_data()
        
    except Exception as e:
        logging.error(f"Error during database initialization: {e}")
        raise


def seed_default_data():
    """
    Seed the database with default data if it's empty
    """
    try:
        from django.contrib.auth.models import User
        from django.core.management import call_command
        
        # Check if admin user exists
        if not User.objects.filter(username='admin').exists():
            # Create default admin user
            User.objects.create_superuser('admin', 'admin@pharmacyerp.com', 'admin123')
        
        # Run seed commands for default data
        # These would be custom management commands for seeding charts of accounts, etc.
        try:
            call_command('seed_payments', verbosity=0)
        except Exception:
            pass  # Payment seeding command might not exist
            
    except Exception as e:
        logging.error(f"Error during data seeding: {e}")


def start_backend_server():
    """
    Start the Django backend server
    """
    import threading
    from django.core.management import call_command
    import socket
    
    def run_server():
        try:
            # Find an available port
            port = 8000
            while True:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:
                    break  # Port is available
                port += 1
            
            call_command('runserver', f'127.0.0.1:{port}', verbosity=0)
        except Exception as e:
            logging.error(f"Backend server failed to start: {e}")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_server, daemon=True)
    backend_thread.start()
    
    return port


def main():
    """
    Main startup process
    """
    # Setup logging
    from config.production_config import get_log_path
    log_path = get_log_path()
    logging.basicConfig(
        filename=os.path.join(log_path, 'pharmacy_erp.log'),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Setup environment
        base_dir = setup_environment()
        
        # Initialize Django
        initialize_django()
        
        # Run database migrations
        run_database_migrations()
        
        # Start backend server
        backend_port = start_backend_server()
        
        # Set environment variable for frontend to know backend URL
        os.environ['PHARMACY_ERP_BACKEND_PORT'] = str(backend_port)
        os.environ['PHARMACY_ERP_BACKEND_URL'] = f'http://127.0.0.1:{backend_port}'
        
        # Start the frontend application
        from frontend.main import main as frontend_main
        frontend_main()
        
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Show error to user
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Startup Error",
            f"Pharmacy ERP failed to start:\n\n{str(e)}\n\nCheck logs for details: {get_log_path()}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
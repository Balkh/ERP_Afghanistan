"""
Enhanced startup script for packaged application
This is the entry point for the PyInstaller executable
"""
import sys
import os
import logging
from pathlib import Path


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and PyInstaller
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def setup_logging():
    """
    Setup logging for the application
    """
    if getattr(sys, 'frozen', False):
        # Use AppData directory for logs in production
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_dir = os.path.join(appdata, 'PharmacyERP', 'logs')
    else:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        filename=os.path.join(log_dir, 'pharmacy_erp.log'),
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Pharmacy ERP starting up...")


def initialize_backend():
    """
    Initialize the Django backend
    """
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Add backend to path
    backend_path = get_resource_path('backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    # Import and setup Django
    import django
    django.setup()
    
    # Run migrations
    from django.core.management import call_command
    try:
        call_command('migrate', verbosity=0)
    except Exception as e:
        logging.warning(f"Migration warning: {e}")
    
    # Create cache tables if needed
    try:
        call_command('createcachetable', verbosity=0)
    except Exception:
        pass  # Cache table creation might fail if not needed


def start_backend():
    """
    Start the Django backend server in a thread
    """
    import threading
    import socket
    from django.core.management import call_command
    
    def run_server():
        try:
            # Find available port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
            
            # Store port in a file for frontend to read
            port_file = get_resource_path('backend_port.txt')
            with open(port_file, 'w') as f:
                f.write(str(port))
            
            logging.info(f"Starting backend server on port {port}")
            call_command('runserver', f'127.0.0.1:{port}', verbosity=0)
        except Exception as e:
            logging.error(f"Backend server error: {e}")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread


def start_frontend():
    """
    Start the PySide6 frontend
    """
    import time
    
    # Wait for backend to start
    time.sleep(2)
    
    # Read backend port
    port_file = get_resource_path('backend_port.txt')
    backend_url = 'http://127.0.0.1:8000'  # default
    
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                port = f.read().strip()
                backend_url = f'http://127.0.0.1:{port}'
        except (FileNotFoundError, ValueError, OSError):
            pass
    
    # Set backend URL for frontend
    os.environ['PHARMACY_ERP_BACKEND_URL'] = backend_url
    
    # Start frontend
    from frontend.main import main as frontend_main
    frontend_main()


def main():
    """
    Main application entry point
    """
    try:
        setup_logging()
        logging.info("Initializing Pharmacy ERP...")
        
        # Initialize backend
        initialize_backend()
        logging.info("Backend initialized")
        
        # Start backend server
        backend_thread = start_backend()
        logging.info("Backend server started")
        
        # Start frontend
        start_frontend()
        
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
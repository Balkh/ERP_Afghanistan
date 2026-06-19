"""
Pharmacy ERP Startup Configuration
Handles the complete startup process for the packaged application
"""
import os
import sys
import time
import socket
import logging
import subprocess
from pathlib import Path


class PharmacyERPStartup:
    """
    Manages the startup process for the packaged Pharmacy ERP application
    """
    
    def __init__(self):
        self.base_dir = self._get_base_dir()
        self.data_dir = self._get_data_dir()
        self.log_dir = self._get_log_dir()
        self.config_dir = self._get_config_dir()
        self.backend_process = None
        self.backend_port = None
        
    def _get_base_dir(self):
        """Get the base directory for the application"""
        if getattr(sys, 'frozen', False):
            return Path(os.path.dirname(sys.executable))
        else:
            return Path(__file__).resolve().parent.parent.parent
    
    def _get_data_dir(self):
        """Get the data directory"""
        if getattr(sys, 'frozen', False):
            appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
            data_dir = Path(appdata) / 'PharmacyERP' / 'data'
        else:
            data_dir = self.base_dir / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def _get_log_dir(self):
        """Get the log directory"""
        if getattr(sys, 'frozen', False):
            appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
            log_dir = Path(appdata) / 'PharmacyERP' / 'logs'
        else:
            log_dir = self.base_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    
    def _get_config_dir(self):
        """Get the config directory"""
        if getattr(sys, 'frozen', False):
            appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
            config_dir = Path(appdata) / 'PharmacyERP' / 'config'
        else:
            config_dir = self.base_dir / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.log_dir / 'startup.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Pharmacy ERP startup initiated")
    
    def initialize_environment(self):
        """Initialize the application environment"""
        self.logger.info("Initializing environment...")
        
        # Create necessary directories
        directories = [
            self.data_dir,
            self.log_dir,
            self.config_dir,
            self.data_dir / 'media',
            self.data_dir / 'temp',
            self.data_dir / 'backups',
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created directory: {directory}")
        
        # Set environment variables
        os.environ['PHARMACY_ERP_DATA_DIR'] = str(self.data_dir)
        os.environ['PHARMACY_ERP_LOG_DIR'] = str(self.log_dir)
        os.environ['PHARMACY_ERP_CONFIG_DIR'] = str(self.config_dir)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'
        
        # Add backend to Python path
        backend_path = self.base_dir / 'backend'
        if backend_path.exists() and str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
    
    def initialize_database(self):
        """Initialize the database"""
        self.logger.info("Initializing database...")
        
        try:
            import django
            from django.conf import settings
            
            # Ensure Django is configured
            if not settings.configured:
                from config.settings_production import *
            
            django.setup()
            
            # Run migrations
            from django.core.management import call_command
            self.logger.info("Running database migrations...")
            call_command('migrate', verbosity=0)
            
            # Seed default data if needed
            self._seed_default_data()
            
            self.logger.info("Database initialization complete")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def _seed_default_data(self):
        """Seed default data if database is empty"""
        try:
            from django.contrib.auth.models import User
            from django.core.management import call_command
            
            # Check if admin user exists
            if not User.objects.filter(username='admin').exists():
                self.logger.info("Creating default admin user...")
                User.objects.create_superuser(
                    'admin',
                    'admin@pharmacyerp.com',
                    'admin123'
                )
                self.logger.info("Default admin user created")
            
            # Try to run seed commands
            try:
                call_command('seed_payments', verbosity=0)
                self.logger.info("Payment data seeded")
            except Exception:
                pass  # Seed command might not exist
                
        except Exception as e:
            self.logger.warning(f"Data seeding warning: {e}")
    
    def find_available_port(self, start_port=8000):
        """Find an available port for the backend server"""
        port = start_port
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port))
                    return port
                except OSError:
                    port += 1
    
    def start_backend_server(self):
        """Start the Django backend server"""
        self.logger.info("Starting backend server...")
        
        self.backend_port = self.find_available_port()
        self.logger.info(f"Using backend port: {self.backend_port}")
        
        # Save port to file for frontend to read
        port_file = self.config_dir / 'backend_port.txt'
        port_file.write_text(str(self.backend_port))
        
        # Set environment variable for frontend
        os.environ['PHARMACY_ERP_BACKEND_URL'] = f'http://127.0.0.1:{self.backend_port}'
        
        # Start Django server in a subprocess
        try:
            import django
            from django.core.management import call_command
            import threading
            
            def run_server():
                try:
                    call_command('runserver', f'127.0.0.1:{self.backend_port}', verbosity=0)
                except Exception as e:
                    self.logger.error(f"Backend server error: {e}")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            self.logger.info("Backend server started in thread")
            
        except Exception as e:
            self.logger.error(f"Failed to start backend server: {e}")
            raise
    
    def start_frontend(self):
        """Start the PySide6 frontend application"""
        self.logger.info("Starting frontend application...")
        
        # Import and run frontend
        from frontend.main import main as frontend_main
        frontend_main()
    
    def run(self):
        """Run the complete startup process"""
        try:
            # Step 1: Setup logging
            self.setup_logging()
            
            # Step 2: Initialize environment
            self.initialize_environment()
            
            # Step 3: Initialize database
            self.initialize_database()
            
            # Step 4: Start backend server
            self.start_backend_server()
            
            # Step 5: Start frontend
            self.start_frontend()
            
        except KeyboardInterrupt:
            self.logger.info("Application shutdown requested")
        except Exception as e:
            self.logger.error(f"Application startup failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            sys.exit(1)
        finally:
            self.logger.info("Application shutdown complete")


def main():
    """Main entry point"""
    startup = PharmacyERPStartup()
    startup.run()


if __name__ == "__main__":
    main()
"""
Pharmacy ERP First-Run Setup Wizard
Handles initial configuration, admin creation, and database initialization
"""
import os
import sys
import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path


class FirstRunSetup:
    """
    Manages the first-run setup process for Pharmacy ERP
    """
    
    def __init__(self, app_data_dir=None):
        if app_data_dir is None:
            if os.name == 'nt':
                app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'PharmacyERP')
            else:
                app_data_dir = os.path.join(os.path.expanduser('~'), '.pharmacy_erp')
        
        self.app_data_dir = Path(app_data_dir)
        self.config_dir = self.app_data_dir / 'config'
        self.data_dir = self.app_data_dir / 'data'
        self.db_path = self.data_dir / 'pharmacy_erp.db'
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def is_first_run(self):
        """Check if this is the first run of the application"""
        setup_file = self.config_dir / 'setup_completed.flag'
        return not setup_file.exists()
    
    def mark_setup_complete(self):
        """Mark the setup as complete"""
        setup_file = self.config_dir / 'setup_completed.flag'
        setup_file.touch()
    
    def generate_secret_key(self):
        """Generate a secure Django secret key"""
        return secrets.token_urlsafe(50)
    
    def hash_password(self, password, salt=None):
        """Hash password for secure storage"""
        if salt is None:
            salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return (salt + pwd_hash).decode('utf-8')
    
    def check_database_exists(self):
        """Check if the database file exists"""
        return self.db_path.exists()
    
    def create_admin_user(self, username, password, email, first_name='Admin', last_name='User'):
        """Create admin user in the database"""
        if not self.check_database_exists():
            return False, "Database does not exist"
        
        try:
            # Connect to Django database
            import django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()
            
            from django.contrib.auth.models import User
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                return False, f"User '{username}' already exists"
            
            # Create superuser
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            return True, f"Admin user '{username}' created successfully"
            
        except Exception as e:
            return False, f"Error creating admin user: {str(e)}"
    
    def initialize_database(self):
        """Initialize the database with Django migrations"""
        try:
            import django
            from django.conf import settings
            from django.core.management import call_command
            
            # Configure Django if not already configured
            if not settings.configured:
                settings.configure(
                    DATABASES={
                        'default': {
                            'ENGINE': 'django.db.backends.sqlite3',
                            'NAME': str(self.db_path),
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
                )
            
            django.setup()
            
            # Run migrations
            call_command('migrate', verbosity=1)
            
            # Create cache table
            try:
                call_command('createcachetable', verbosity=0)
            except Exception:
                pass  # Cache table might not be needed
            
            return True, "Database initialized successfully"
            
        except Exception as e:
            return False, f"Error initializing database: {str(e)}"
    
    def seed_default_data(self):
        """Seed the database with default data"""
        try:
            import django
            from django.core.management import call_command
            
            # Seed payment methods and accounts
            try:
                call_command('seed_payments', verbosity=1)
            except Exception as e:
                print(f"Warning: Could not seed payment data: {e}")
            
            # Initialize chart of accounts
            try:
                from accounting.services.account_hierarchy import AccountHierarchyService
                created = AccountHierarchyService.initialize_default_chart()
                print(f"Created {len(created)} default accounts")
            except Exception as e:
                print(f"Warning: Could not initialize chart of accounts: {e}")
            
            return True, "Default data seeded successfully"
            
        except Exception as e:
            return False, f"Error seeding default data: {str(e)}"
    
    def seed_company(self, company_name, currency='AFN'):
        """Create the Company model entry (SSOT for business config).

        This replaces the old pattern of writing company_name to config.json.
        All business config MUST be stored in the Company model.
        """
        try:
            import django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()
            
            from core.models.system import Company
            
            if Company.objects.filter(is_active=True).exists():
                return True, "Company already exists"
            
            company = Company.objects.create(
                name=company_name,
                code=company_name[:20].upper().replace(' ', '_'),
                default_currency=currency,
                is_active=True,
            )
            return True, f"Company '{company_name}' created in database"
            
        except Exception as e:
            return False, f"Error creating company: {str(e)}"
    
    def create_config_file(self, config_data):
        """Create configuration file with user settings.

        DEPRECATED: This method no longer writes business config to JSON.
        Business configuration (company_name, currency, etc.) is stored in the
        Company model via Django ORM. This method only creates a technical
        metadata file for installer tracking purposes.
        """
        import json
        
        config = {
            'version': '1.0.0',
            'setup_date': datetime.now().isoformat(),
            'app_name': config_data.get('app_name', 'Pharmacy ERP'),
            'admin_username': config_data.get('admin_username', 'admin'),
            'admin_email': config_data.get('admin_email', ''),
            'language': config_data.get('language', 'en'),
            'timezone': config_data.get('timezone', 'UTC'),
            'database_path': str(self.db_path),
            'log_level': config_data.get('log_level', 'INFO'),
            'backup_enabled': config_data.get('backup_enabled', True),
            'backup_interval': config_data.get('backup_interval', 'daily'),
            'DEPRECATED': 'company_name and currency are now stored in Company model, not this file',
        }
        
        config_file = self.config_dir / 'config.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True, "Configuration file created (business config stored in Company model)"
    
    def run_setup_wizard(self, admin_username='admin', admin_password='admin123', 
                        admin_email='admin@pharmacyerp.com', company_name='Pharmacy ERP',
                        currency='AFN'):
        """Run the complete first-run setup process"""
        results = []
        
        print("=" * 60)
        print("Pharmacy ERP - First Run Setup")
        print("=" * 60)
        
        # Step 1: Check if setup is needed
        if not self.is_first_run():
            print("Setup has already been completed. Skipping first-run setup.")
            return True, "Setup already completed"
        
        # Step 2: Initialize database
        print("\n[1/6] Initializing database...")
        success, message = self.initialize_database()
        results.append(('Database Initialization', success, message))
        if not success:
            return False, f"Database initialization failed: {message}"
        print(f"  ✓ {message}")
        
        # Step 3: Create admin user
        print("\n[2/6] Creating admin user...")
        success, message = self.create_admin_user(
            username=admin_username,
            password=admin_password,
            email=admin_email
        )
        results.append(('Admin User Creation', success, message))
        if not success:
            return False, f"Admin user creation failed: {message}"
        print(f"  ✓ {message}")
        
        # Step 4: Seed default data
        print("\n[3/6] Seeding default data...")
        success, message = self.seed_default_data()
        results.append(('Default Data Seeding', success, message))
        if not success:
            print(f"  ⚠ Warning: {message}")
        else:
            print(f"  ✓ {message}")
        
        # Step 5: Create company in database (SSOT)
        print("\n[4/6] Creating company in database...")
        success, message = self.seed_company(
            company_name=company_name,
            currency=currency
        )
        results.append(('Company Creation (SSOT)', success, message))
        if not success:
            print(f"  ⚠ Warning: {message}")
        else:
            print(f"  ✓ {message}")
        
        # Step 6: Create configuration file (technical metadata only)
        print("\n[5/6] Creating configuration file...")
        config_data = {
            'app_name': 'Pharmacy ERP',
            'company_name': company_name,
            'admin_username': admin_username,
            'admin_email': admin_email,
        }
        success, message = self.create_config_file(config_data)
        results.append(('Configuration Creation', success, message))
        if not success:
            return False, f"Configuration creation failed: {message}"
        print(f"  ✓ {message}")
        
        # Step 7: Mark setup as complete
        print("\n[6/6] Completing setup...")
        self.mark_setup_complete()
        results.append(('Setup Completion', True, 'Setup marked as complete'))
        print("  ✓ Setup completed successfully")
        
        # Summary
        print("\n" + "=" * 60)
        print("Setup Summary:")
        print("=" * 60)
        for step_name, success, message in results:
            status = "✓" if success else "✗"
            print(f"  {status} {step_name}: {message}")
        
        print("\nDefault Login Credentials:")
        print(f"  Username: {admin_username}")
        print(f"  Password: {admin_password}")
        print("\n⚠ IMPORTANT: Change the default password after first login!")
        print("=" * 60)
        
        return True, "First-run setup completed successfully"


class SetupWizardUI:
    """
    GUI-based setup wizard using Tkinter
    """
    
    def __init__(self):
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox
            self.tk = tk
            self.ttk = ttk
            self.messagebox = messagebox
        except ImportError:
            print("Tkinter not available. Use command-line setup instead.")
            self.tk = None
    
    def run_gui_setup(self):
        """Run the GUI-based setup wizard"""
        if not self.tk:
            print("GUI not available. Run command-line setup.")
            return False
        
        root = self.tk.Tk()
        root.title("Pharmacy ERP - First Run Setup")
        root.geometry("500x400")
        root.resizable(False, False)
        
        # Center window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (500 // 2)
        y = (root.winfo_screenheight() // 2) - (400 // 2)
        root.geometry(f"+{x}+{y}")
        
        # Variables
        company_var = self.tk.StringVar(value="Pharmacy ERP")
        admin_user_var = self.tk.StringVar(value="admin")
        admin_email_var = self.tk.StringVar(value="admin@pharmacyerp.com")
        admin_pass_var = self.tk.StringVar(value="admin123")
        admin_confirm_var = self.tk.StringVar()
        
        def on_setup():
            if admin_pass_var.get() != admin_confirm_var.get():
                self.messagebox.showerror("Error", "Passwords do not match!")
                return
            
            if len(admin_pass_var.get()) < 6:
                self.messagebox.showerror("Error", "Password must be at least 6 characters!")
                return
            
            root.destroy()
            
            # Run setup
            setup = FirstRunSetup()
            success, message = setup.run_setup_wizard(
                admin_username=admin_user_var.get(),
                admin_password=admin_pass_var.get(),
                admin_email=admin_email_var.get(),
                company_name=company_var.get()
            )
            
            if success:
                self.messagebox.showinfo("Success", message)
            else:
                self.messagebox.showerror("Error", message)
        
        # Title
        title_label = self.ttk.Label(root, text="Pharmacy ERP Setup Wizard", 
                                     font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # Form frame
        form_frame = self.ttk.Frame(root, padding=20)
        form_frame.pack(fill="both", expand=True)
        
        # Company Name
        self.ttk.Label(form_frame, text="Company Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.ttk.Entry(form_frame, textvariable=company_var, width=40).grid(row=0, column=1, pady=5)
        
        # Admin Username
        self.ttk.Label(form_frame, text="Admin Username:").grid(row=1, column=0, sticky="w", pady=5)
        self.ttk.Entry(form_frame, textvariable=admin_user_var, width=40).grid(row=1, column=1, pady=5)
        
        # Admin Email
        self.ttk.Label(form_frame, text="Admin Email:").grid(row=2, column=0, sticky="w", pady=5)
        self.ttk.Entry(form_frame, textvariable=admin_email_var, width=40).grid(row=2, column=1, pady=5)
        
        # Admin Password
        self.ttk.Label(form_frame, text="Admin Password:").grid(row=3, column=0, sticky="w", pady=5)
        self.ttk.Entry(form_frame, textvariable=admin_pass_var, width=40, show="*").grid(row=3, column=1, pady=5)
        
        # Confirm Password
        self.ttk.Label(form_frame, text="Confirm Password:").grid(row=4, column=0, sticky="w", pady=5)
        self.ttk.Entry(form_frame, textvariable=admin_confirm_var, width=40, show="*").grid(row=4, column=1, pady=5)
        
        # Warning label
        warning = self.ttk.Label(form_frame, 
                               text="⚠ Change default password after first login!",
                               foreground="red")
        warning.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Setup button
        setup_btn = self.ttk.Button(form_frame, text="Complete Setup", command=on_setup)
        setup_btn.grid(row=6, column=0, columnspan=2, pady=20)
        
        root.mainloop()
        return True


def main():
    """Main entry point for first-run setup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pharmacy ERP First-Run Setup')
    parser.add_argument('--gui', action='store_true', help='Run GUI setup wizard')
    parser.add_argument('--username', default='admin', help='Admin username')
    parser.add_argument('--password', default='admin123', help='Admin password')
    parser.add_argument('--email', default='admin@pharmacyerp.com', help='Admin email')
    parser.add_argument('--company', default='Pharmacy ERP', help='Company name')
    
    args = parser.parse_args()
    
    if args.gui:
        wizard = SetupWizardUI()
        wizard.run_gui_setup()
    else:
        setup = FirstRunSetup()
        success, message = setup.run_setup_wizard(
            admin_username=args.username,
            admin_password=args.password,
            admin_email=args.email,
            company_name=args.company
        )
        
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
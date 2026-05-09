"""
Pharmacy ERP Installer Workflow Configuration
Defines the complete installation process and workflows
"""

# Installer Workflow Configuration
INSTALLER_CONFIG = {
    # Application Information
    'app': {
        'name': 'Pharmacy ERP',
        'version': '1.0.0',
        'publisher': 'Pharmacy ERP Solutions',
        'description': 'Enterprise Pharmacy Management System',
        'url': 'https://pharmacyerp.example.com',
        'icon': 'frontend/static/icon.ico',
        'executable': 'PharmacyERP.exe',
    },
    
    # Installation Directories
    'directories': {
        'install_dir': '{PROGRAMFILES64}\\PharmacyERP',
        'app_data': '{APPDATA}\\PharmacyERP',
        'data': '{APPDATA}\\PharmacyERP\\data',
        'logs': '{APPDATA}\\PharmacyERP\\logs',
        'config': '{APPDATA}\\PharmacyERP\\config',
        'backups': '{APPDATA}\\PharmacyERP\\backups',
        'media': '{APPDATA}\\PharmacyERP\\media',
        'temp': '{APPDATA}\\PharmacyERP\\temp',
    },
    
    # Shortcuts
    'shortcuts': {
        'start_menu': '{SMPROGRAMS}\\PharmacyERP\\Pharmacy ERP.lnk',
        'desktop': '{DESKTOP}\\Pharmacy ERP.lnk',
        'uninstall': '{SMPROGRAMS}\\PharmacyERP\\Uninstall.lnk',
    },
    
    # Registry Keys
    'registry': {
        'app_key': 'HKLM\\Software\\PharmacyERP',
        'uninstall_key': 'HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PharmacyERP',
        'values': {
            'InstallLocation': '{INSTALLDIR}',
            'Version': '1.0.0',
            'Publisher': 'Pharmacy ERP Solutions',
            'FirstRun': 1,
        },
    },
    
    # File Associations (optional)
    'file_associations': {
        # '.perp': 'PharmacyERP.Backup',  # Backup files
    },
    
    # Environment Variables
    'environment': {
        'PHARMACY_ERP_HOME': '{INSTALLDIR}',
        'PHARMACY_ERP_DATA': '{APPDATA}\\PharmacyERP\\data',
    },
    
    # Dependencies
    'dependencies': {
        'visual_cpp_redistributable': {
            'required': True,
            'url': 'https://aka.ms/vs/17/release/vc_redist.x64.exe',
            'silent_args': '/quiet /norestart',
        },
        # .NET Framework check (if needed)
    },
    
    # Pre-installation Checks
    'pre_install_checks': [
        {
            'type': 'os_version',
            'min_version': '6.1',  # Windows 7 or higher
            'message': 'Windows 7 or higher is required',
        },
        {
            'type': 'disk_space',
            'required_mb': 500,
            'message': '500 MB of free disk space is required',
        },
        {
            'type': 'admin_rights',
            'required': True,
            'message': 'Administrator privileges are required',
        },
        {
            'type': 'port_check',
            'port': 8000,
            'warning': 'Port 8000 is in use. The application will use an alternative port.',
        },
    ],
    
    # Installation Steps
    'install_steps': [
        {
            'id': 'copy_files',
            'name': 'Copy Application Files',
            'description': 'Installing application files to {INSTALLDIR}',
            'action': 'copy',
            'source': 'dist\\PharmacyERP\\*.*',
            'destination': '{INSTALLDIR}',
        },
        {
            'id': 'create_dirs',
            'name': 'Create Data Directories',
            'description': 'Creating application data directories',
            'action': 'create_directories',
            'directories': ['data', 'logs', 'config', 'backups', 'media', 'temp'],
        },
        {
            'id': 'create_shortcuts',
            'name': 'Create Shortcuts',
            'description': 'Creating Start Menu and Desktop shortcuts',
            'action': 'create_shortcuts',
        },
        {
            'id': 'write_registry',
            'name': 'Write Registry Entries',
            'description': 'Writing application registry entries',
            'action': 'write_registry',
        },
        {
            'id': 'setup_uninstaller',
            'name': 'Setup Uninstaller',
            'description': 'Creating uninstaller',
            'action': 'create_uninstaller',
        },
        {
            'id': 'first_run_flag',
            'name': 'Set First Run Flag',
            'description': 'Marking application for first-run setup',
            'action': 'set_first_run',
        },
    ],
    
    # Post-Installation Tasks
    'post_install_tasks': [
        {
            'id': 'launch_setup',
            'name': 'Launch First-Run Setup',
            'description': 'Launch the first-run setup wizard',
            'action': 'launch',
            'executable': '{INSTALLDIR}\\PharmacyERP.exe',
            'args': '--setup',
            'condition': 'first_run',
        },
    ],
    
    # Uninstallation Steps
    'uninstall_steps': [
        {
            'id': 'stop_processes',
            'name': 'Stop Running Processes',
            'description': 'Stopping Pharmacy ERP processes',
            'action': 'stop_process',
            'process_name': 'PharmacyERP.exe',
        },
        {
            'id': 'remove_files',
            'name': 'Remove Application Files',
            'description': 'Removing application files',
            'action': 'remove_directory',
            'directory': '{INSTALLDIR}',
        },
        {
            'id': 'remove_shortcuts',
            'name': 'Remove Shortcuts',
            'description': 'Removing shortcuts',
            'action': 'remove_shortcuts',
        },
        {
            'id': 'remove_registry',
            'name': 'Remove Registry Entries',
            'description': 'Removing registry entries',
            'action': 'remove_registry',
        },
        {
            'id': 'preserve_data',
            'name': 'Preserve User Data',
            'description': 'User data in {APPDATA}\\PharmacyERP will be preserved',
            'action': 'preserve',
            'directory': '{APPDATA}\\PharmacyERP',
        },
    ],
    
    # Uninstall Options
    'uninstall_options': {
        'preserve_data': True,
        'confirm_data_removal': True,
        'data_removal_warning': 'This will permanently delete all your data including database, logs, and backups!',
    },
}


# Workflow States
WORKFLOW_STATES = {
    'NOT_INSTALLED': 'Application is not installed',
    'INSTALLING': 'Installation in progress',
    'INSTALLED': 'Application is installed',
    'FIRST_RUN': 'First-run setup required',
    'READY': 'Application is ready to use',
    'UPDATING': 'Update in progress',
    'UNINSTALLING': 'Uninstallation in progress',
    'ERROR': 'Installation error occurred',
}


# Installer Exit Codes
EXIT_CODES = {
    'SUCCESS': 0,
    'USER_CANCELLED': 1,
    'PREREQUISITE_FAILED': 2,
    'INSTALL_FAILED': 3,
    'UNINSTALL_FAILED': 4,
    'UPDATE_FAILED': 5,
    'ERROR': 99,
}


def get_workflow_description(state):
    """Get description for a workflow state"""
    return WORKFLOW_STATES.get(state, 'Unknown state')


def get_exit_code_description(code):
    """Get description for an exit code"""
    for name, value in EXIT_CODES.items():
        if value == code:
            return name
    return 'Unknown exit code'


if __name__ == '__main__':
    import json
    print("Pharmacy ERP Installer Workflow Configuration")
    print("=" * 50)
    print(json.dumps(INSTALLER_CONFIG, indent=2))
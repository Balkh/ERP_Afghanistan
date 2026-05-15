"""
Management command to seed default roles and permissions.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from security.models import Role, Permission as SecurityPermission, RolePermission


class Command(BaseCommand):
    help = 'Seed default roles and permissions for the ERP system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding roles and permissions...')

        permissions_config = [
            {'module': 'inventory', 'codename': 'inv_view_product', 'name': 'View Products'},
            {'module': 'inventory', 'codename': 'inv_add_product', 'name': 'Add Products'},
            {'module': 'inventory', 'codename': 'inv_change_product', 'name': 'Edit Products'},
            {'module': 'inventory', 'codename': 'inv_delete_product', 'name': 'Delete Products'},
            {'module': 'inventory', 'codename': 'inv_view_category', 'name': 'View Categories'},
            {'module': 'inventory', 'codename': 'inv_view_warehouse', 'name': 'View Warehouses'},
            {'module': 'inventory', 'codename': 'inv_view_batch', 'name': 'View Batches'},
            {'module': 'sales', 'codename': 'sales_view_invoice', 'name': 'View Sales Invoices'},
            {'module': 'sales', 'codename': 'sales_add_invoice', 'name': 'Create Sales Invoices'},
            {'module': 'sales', 'codename': 'sales_change_invoice', 'name': 'Edit Sales Invoices'},
            {'module': 'sales', 'codename': 'sales_delete_invoice', 'name': 'Delete Sales Invoices'},
            {'module': 'purchases', 'codename': 'pur_view_invoice', 'name': 'View Purchase Invoices'},
            {'module': 'purchases', 'codename': 'pur_add_invoice', 'name': 'Create Purchase Invoices'},
            {'module': 'purchases', 'codename': 'pur_change_invoice', 'name': 'Edit Purchase Invoices'},
            {'module': 'accounting', 'codename': 'acc_view_account', 'name': 'View Accounts'},
            {'module': 'accounting', 'codename': 'acc_view_journal', 'name': 'View Journal Entries'},
            {'module': 'accounting', 'codename': 'acc_add_journal', 'name': 'Create Journal Entries'},
            {'module': 'payments', 'codename': 'pay_view_payment', 'name': 'View Payments'},
            {'module': 'payments', 'codename': 'pay_add_payment', 'name': 'Create Payments'},
            {'module': 'hr', 'codename': 'hr_view_employee', 'name': 'View Employees'},
            {'module': 'hr', 'codename': 'hr_add_employee', 'name': 'Add Employees'},
            {'module': 'payroll', 'codename': 'payroll_view_salary', 'name': 'View Salary'},
            {'module': 'security', 'codename': 'sec_view_role', 'name': 'View Roles'},
            {'module': 'security', 'codename': 'sec_add_role', 'name': 'Add Roles'},
            {'module': 'security', 'codename': 'sec_change_role', 'name': 'Edit Roles'},
            {'module': 'security', 'codename': 'sec_delete_role', 'name': 'Delete Roles'},
        ]

        created_perms = {}
        for perm_config in permissions_config:
            try:
                perm, created = SecurityPermission.objects.get_or_create(
                    codename=perm_config['codename'],
                    defaults={
                        'name': perm_config['name'],
                        'module': perm_config['module'],
                        'description': f'{perm_config["name"]} for {perm_config["module"]}',
                        'is_active': True
                    }
                )
                created_perms[perm_config['codename']] = perm
                if created:
                    self.stdout.write(f'  Created permission: {perm}')
            except Exception as e:
                perm = SecurityPermission.objects.filter(codename=perm_config['codename']).first()
                if perm:
                    created_perms[perm_config['codename']] = perm
                else:
                    self.stdout.write(self.style.ERROR(f'  Failed: {perm_config["codename"]} - {e}'))

        roles_config = {
            'Admin': {
                'description': 'Full system access',
                'permissions': list(created_perms.keys())
            },
            'Manager': {
                'description': 'Manage operations',
                'permissions': [
                    'inv_view_product', 'inv_add_product', 'inv_change_product',
                    'inv_view_category', 'inv_view_warehouse', 'inv_view_batch',
                    'sales_view_invoice', 'sales_add_invoice', 'sales_change_invoice',
                    'pur_view_invoice', 'pur_add_invoice', 'pur_change_invoice',
                    'acc_view_account', 'acc_view_journal', 'acc_add_journal',
                    'pay_view_payment', 'pay_add_payment',
                    'hr_view_employee', 'payroll_view_salary'
                ]
            },
            'Pharmacist': {
                'description': 'Pharmacy operations',
                'permissions': [
                    'inv_view_product', 'inv_view_category', 'inv_view_warehouse', 'inv_view_batch',
                    'sales_view_invoice', 'sales_add_invoice', 'sales_change_invoice'
                ]
            },
            'Cashier': {
                'description': 'Point of sale',
                'permissions': [
                    'sales_view_invoice', 'sales_add_invoice',
                    'inv_view_product', 'inv_view_batch'
                ]
            },
            'Accountant': {
                'description': 'Financial operations',
                'permissions': [
                    'acc_view_account', 'acc_view_journal', 'acc_add_journal',
                    'pur_view_invoice', 'pur_add_invoice',
                    'pay_view_payment', 'pay_add_payment'
                ]
            }
        }

        for role_name, role_config in roles_config.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': role_config['description'],
                    'is_active': True
                }
            )

            if created:
                self.stdout.write(f'  Created role: {role_name}')

            for perm_codename in role_config['permissions']:
                if perm_codename in created_perms:
                    RolePermission.objects.get_or_create(
                        role=role,
                        permission=created_perms[perm_codename]
                    )

        self.stdout.write(self.style.SUCCESS('Roles and permissions seeded successfully!'))

        user_count = User.objects.count()
        if user_count == 0:
            self.stdout.write(self.style.WARNING('No users exist. Creating default admin user...'))
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@pharmacy.local',
                password=temp_password,
                first_name='System',
                last_name='Administrator'
            )
            admin_role = Role.objects.get(name='Admin')
            from security.models import UserRole
            UserRole.objects.create(user=admin_user, role=admin_role)
            self.stdout.write(self.style.SUCCESS(
                f'Created default admin user (username: admin, password: {temp_password})'
            ))
            self.stdout.write(self.style.WARNING(
                '⚠️  CHANGE THIS PASSWORD IMMEDIATELY via /api/auth/change-password/'
            ))
        else:
            self.stdout.write(f'Users exist: {user_count} users')
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dashboard.models import DashboardAdmin
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a dashboard admin user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Admin email')
        parser.add_argument('--username', type=str, required=True, help='Admin username')
        parser.add_argument('--password', type=str, required=True, help='Admin password')
        parser.add_argument('--first-name', type=str, default='', help='Admin first name')
        parser.add_argument('--last-name', type=str, default='', help='Admin last name')
        parser.add_argument('--permissions', type=str, default='all', 
                          help='Comma-separated permissions (products,orders,payments,analytics) or "all"')

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        permissions = options['permissions']

        try:
            with transaction.atomic():
                # Create or get user
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_active': True,
                        'is_verified': True
                    }
                )

                if created:
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Created user: {email}')
                    )
                else:
                    # Update existing user
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated user: {email}')
                    )

                # Set permissions
                if permissions == 'all':
                    dashboard_permissions = {
                        'products': True,
                        'orders': True,
                        'payments': True,
                        'analytics': True
                    }
                else:
                    permission_list = [p.strip() for p in permissions.split(',')]
                    dashboard_permissions = {
                        'products': 'products' in permission_list,
                        'orders': 'orders' in permission_list,
                        'payments': 'payments' in permission_list,
                        'analytics': 'analytics' in permission_list
                    }

                # Create or update dashboard admin
                dashboard_admin, created = DashboardAdmin.objects.get_or_create(
                    user=user,
                    defaults={
                        'is_dashboard_admin': True,
                        'dashboard_permissions': dashboard_permissions,
                        'two_factor_enabled': False
                    }
                )

                if not created:
                    dashboard_admin.is_dashboard_admin = True
                    dashboard_admin.dashboard_permissions = dashboard_permissions
                    dashboard_admin.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Dashboard admin created/updated successfully!\n'
                        f'Email: {email}\n'
                        f'Username: {username}\n'
                        f'Permissions: {dashboard_permissions}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating dashboard admin: {str(e)}')
            ) 
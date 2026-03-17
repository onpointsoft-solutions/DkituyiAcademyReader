from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from authentication.models import UserProfile


class Command(BaseCommand):
    help = 'Create a superuser with default credentials'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin')
        parser.add_argument('--email', type=str, default='admin@bookreader.com')
        parser.add_argument('--password', type=str, default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            return

        # Create superuser
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name='Super',
            last_name='Admin'
        )

        # Create user profile
        UserProfile.objects.create(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f'Superuser "{username}" created successfully!\n'
                f'Login: {username}\n'
                f'Password: {password}\n'
                f'Admin URL: http://127.0.0.1:8001/admin/\n'
                f'SuperAdmin URL: http://127.0.0.1:8001/superadmin/'
            )
        )

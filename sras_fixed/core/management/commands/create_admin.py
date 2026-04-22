"""
Auto-create superuser for Render deployment.
Runs during build — if a superuser exists, does nothing.
Uses env vars:
- DJANGO_SUPERUSER_USERNAME
- DJANGO_SUPERUSER_EMAIL
- DJANGO_SUPERUSER_PASSWORD
"""

import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError

User = get_user_model()


class Command(BaseCommand):
    help = 'Auto-create superuser if none exists (for Render deployment)'

    def handle(self, *args, **options):
        try:
            # Check if table exists and superuser already exists
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write(self.style.WARNING(
                    'Superuser already exists. Skipping.'
                ))
                return
        except (OperationalError, ProgrammingError):
            self.stdout.write(self.style.ERROR(
                'Database not ready. Run migrations first.'
            ))
            return

        # Get credentials from environment or fallback
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@sras.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin@123')

        # Create superuser
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Superuser "{username}" created successfully!'
        ))
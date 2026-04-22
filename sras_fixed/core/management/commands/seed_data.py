"""
Management command: seed_data
Creates default Teacher and Student users for Render deployment.

Usage:
    python manage.py seed_data
"""

import datetime
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError, ProgrammingError


class Command(BaseCommand):
    help = 'Create default teacher and student accounts for initial login'

    def handle(self, *args, **options):
        from core.models import Teacher, Student

        # ── Teacher ───────────────────────────────────────────────
        try:
            if not Teacher.objects.filter(email__iexact='teacher@test.com').exists():
                t = Teacher(
                    name='Default Teacher',
                    email='teacher@test.com',
                    is_active=True,
                )
                t.set_password('1234')   # hashes properly via make_password
                t.save()
                self.stdout.write(self.style.SUCCESS(
                    'Created teacher  ->  email: teacher@test.com  password: 1234'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    'Teacher teacher@test.com already exists. Skipping.'
                ))
        except (OperationalError, ProgrammingError) as e:
            self.stdout.write(self.style.ERROR(f'Teacher table error: {e}'))
            return

        # ── Student ───────────────────────────────────────────────
        try:
            if not Student.objects.filter(email__iexact='student@test.com').exists():
                Student.objects.create(
                    name='Default Student',
                    email='student@test.com',
                    gender='Male',
                    date_of_birth=datetime.date(2005, 1, 1),  # DOB password = 01012005
                )
                self.stdout.write(self.style.SUCCESS(
                    'Created student  ->  email: student@test.com  password (DOB): 01012005'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    'Student student@test.com already exists. Skipping.'
                ))
        except (OperationalError, ProgrammingError) as e:
            self.stdout.write(self.style.ERROR(f'Student table error: {e}'))

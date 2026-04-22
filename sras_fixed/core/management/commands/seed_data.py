"""
Management command: seed_data
Creates default Teacher and Student users for Render deployment.

Credentials:
  Teacher  → email: teacher@test.com   password: 1234
  Student  → email: student@test.com   password (DOB): 01012000

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
            teacher = Teacher.objects.filter(email__iexact='teacher@test.com').first()
            if teacher:
                # Ensure password is correct (re-hash if needed)
                if not teacher.check_password('1234'):
                    teacher.set_password('1234')
                    teacher.is_active = True
                    teacher.save()
                    self.stdout.write(self.style.SUCCESS(
                        'Teacher teacher@test.com password reset to: 1234'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        'Teacher teacher@test.com already exists. Skipping.'
                    ))
            else:
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
        except (OperationalError, ProgrammingError) as e:
            self.stdout.write(self.style.ERROR(f'Teacher table error: {e}'))
            return

        # ── Student ───────────────────────────────────────────────
        try:
            student = Student.objects.filter(email__iexact='student@test.com').first()
            if student:
                # Ensure DOB is set correctly for password login
                expected_dob = datetime.date(2000, 1, 1)
                if student.date_of_birth != expected_dob:
                    student.date_of_birth = expected_dob
                    student.save()
                    self.stdout.write(self.style.SUCCESS(
                        'Student student@test.com DOB updated. Password: 01012000'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        'Student student@test.com already exists. Skipping.'
                    ))
            else:
                Student.objects.create(
                    name='Default Student',
                    email='student@test.com',
                    gender='Male',
                    date_of_birth=datetime.date(2000, 1, 1),  # DOB password = 01012000
                )
                self.stdout.write(self.style.SUCCESS(
                    'Created student  ->  email: student@test.com  password (DOB): 01012000'
                ))
        except (OperationalError, ProgrammingError) as e:
            self.stdout.write(self.style.ERROR(f'Student table error: {e}'))

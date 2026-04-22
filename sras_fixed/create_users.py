"""
Standalone user creation script (run via: python manage.py shell < create_users.py)
Creates default Teacher and Student in the custom SRAS models.

NOTE: Prefer using `python manage.py seed_data` instead.
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sras.settings')
django.setup()

import datetime
from core.models import Teacher, Student

# ── Teacher ──────────────────────────────────────────────
teacher, created = Teacher.objects.get_or_create(
    email='teacher@test.com',
    defaults={
        'name': 'Default Teacher',
        'is_active': True,
    }
)
if created:
    teacher.set_password('1234')
    teacher.save()
    print("Created teacher: teacher@test.com / 1234")
else:
    print("Teacher teacher@test.com already exists.")

# ── Student ──────────────────────────────────────────────
student, created = Student.objects.get_or_create(
    email='student@test.com',
    defaults={
        'name': 'Default Student',
        'gender': 'Male',
        'date_of_birth': datetime.date(2000, 1, 1),  # password = 01012000
    }
)
if created:
    print("Created student: student@test.com / 01012000 (DOB)")
else:
    print("Student student@test.com already exists.")

print("Done.")

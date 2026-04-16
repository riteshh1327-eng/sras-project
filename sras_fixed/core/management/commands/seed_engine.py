"""
Management command: seed_engine
Seeds GradeScale with University of Mumbai defaults.

Usage:
    python manage.py seed_engine
"""

from django.core.management.base import BaseCommand
from core.services import seed_grade_scale


class Command(BaseCommand):
    help = 'Seed GradeScale with University of Mumbai grade defaults'

    def handle(self, *args, **options):
        count = seed_grade_scale()
        self.stdout.write(
            self.style.SUCCESS(f'✓ GradeScale seeded with {count} grade rows.')
        )
        self.stdout.write(
            self.style.WARNING(
                '\nNext steps:\n'
                '  1. python manage.py migrate\n'
                '  2. Go to /engine/subjects/ to add semester subjects\n'
                '  3. Go to /results/engine/bulk/ to enter marks\n'
                '  4. Go to /analytics/teacher/ to view class analytics\n'
            )
        )

"""
Django management command to find duplicate DR numbers in the database.

Usage:
    python manage.py find_duplicate_dr
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.deficiencies.models import Deficiency


class Command(BaseCommand):
    help = 'Find duplicate DR numbers in the database'

    def handle(self, *args, **options):
        self.stdout.write('Checking for duplicate DR numbers...')

        # Find DRs that appear more than once
        duplicates = Deficiency.objects.values('deficiency_number') \
            .annotate(count=Count('deficiency_number')) \
            .filter(count__gt=1) \
            .order_by('-count')

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicates found!'))
            return

        self.stdout.write(self.style.WARNING(f'Found {duplicates.count()} DR numbers with duplicates:'))
        self.stdout.write('\nDR#    | Count | Details')
        self.stdout.write('-' * 50)

        total_dupes = 0
        for dup in duplicates:
            dr_num = dup['deficiency_number']
            count = dup['count']
            total_dupes += count

            # Get all records with this DR number
            records = Deficiency.objects.filter(deficiency_number=dr_num)
            self.stdout.write(f'{dr_num} | {count}     | IDs: {list(records.values_list("pk", flat=True))}')

        self.stdout.write('-' * 50)
        self.stdout.write(self.style.ERROR(f'Total duplicate records: {total_dupes - duplicates.count()}'))

        self.stdout.write('\nSuggestions:')
        self.stdout.write('1. Manually review duplicates in Django Admin or database')
        self.stdout.write('2. Keep the oldest/newest record and delete others')
        self.stdout.write('3. Export data, clean duplicates, then re-import')

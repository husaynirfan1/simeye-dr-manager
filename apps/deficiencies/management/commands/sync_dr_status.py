"""
Django management command to sync DR status from two separate text files.

File 1 (DR numbers): dr_numbers.txt
    4452
    4453
    4454

File 2 (Statuses): dr_statuses.txt
    Cleared
    OPEN
    In Work

Files are matched by line position (line 1 = DR#4452 with Status=Cleared)

Usage:
    python manage.py sync_dr_status --numbers dr_numbers.txt --statuses dr_statuses.txt
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from apps.deficiencies.models import Deficiency


class Command(BaseCommand):
    help = 'Sync DR status from two separate text files (numbers and statuses)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--numbers',
            type=str,
            required=True,
            help='Path to text file containing DR numbers (one per line)'
        )
        parser.add_argument(
            '--statuses',
            type=str,
            required=True,
            help='Path to text file containing statuses (one per line)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without actually updating'
        )
        parser.add_argument(
            '--update-all',
            action='store_true',
            help='Update ALL records with same DR number (including different resources)'
        )
        parser.add_argument(
            '--fill-empty-only',
            action='store_true',
            help='Only update DRs where status is NULL/empty in database (interactive mode)'
        )

    def handle(self, *args, **options):
        numbers_file = options['numbers']
        statuses_file = options['statuses']
        dry_run = options['dry_run']
        update_all = options['update_all']
        fill_empty_only = options['fill_empty_only']

        # Read DR numbers (preserve all lines including empty, support <start>/<end> markers)
        try:
            with open(numbers_file, 'r') as f:
                dr_numbers = []
                in_data_range = False
                for line in f:
                    stripped = line.strip()
                    if stripped == '<start>':
                        in_data_range = True
                        continue
                    if stripped == '<end>':
                        in_data_range = False
                        continue
                    if not in_data_range:
                        continue
                    if stripped.startswith('#'):
                        continue
                    dr_numbers.append(stripped if stripped else '')
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {numbers_file}'))
            return

        # Read statuses (preserve all lines including empty, support <start>/<end> markers)
        try:
            with open(statuses_file, 'r') as f:
                statuses = []
                in_data_range = False
                for line in f:
                    stripped = line.strip()
                    if stripped == '<start>':
                        in_data_range = True
                        continue
                    if stripped == '<end>':
                        in_data_range = False
                        continue
                    if not in_data_range:
                        continue
                    if stripped.startswith('#'):
                        continue
                    statuses.append(stripped if stripped else '')
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {statuses_file}'))
            return

        # Check if files have same number of lines
        if len(dr_numbers) != len(statuses):
            self.stderr.write(self.style.ERROR(
                f'File length mismatch: {len(dr_numbers)} DR numbers vs {len(statuses)} statuses'
            ))
            self.stderr.write('Both files must have the same number of lines.')
            return

        self.stdout.write(f'Processing {len(dr_numbers)} DR status updates...')
        if update_all:
            self.stdout.write(self.style.WARNING('Update ALL mode: Will update all records with same DR number'))
        if fill_empty_only:
            self.stdout.write(self.style.WARNING('Fill Empty Only mode: Only updating NULL/empty statuses'))

        # Parse and pair DR numbers with statuses
        updates = []
        parse_errors = []

        for i, (dr_num_str, status) in enumerate(zip(dr_numbers, statuses), 1):
            dr_num_str = dr_num_str.strip('# ')  # Remove '#' if present
            status = status.strip()

            try:
                dr_number = int(dr_num_str)
                updates.append((dr_number, status))
            except ValueError:
                parse_errors.append((i, dr_num_str))
                continue

        if parse_errors:
            self.stderr.write(self.style.WARNING(f'Could not parse {len(parse_errors)} DR numbers:'))
            for line_num, dr_str in parse_errors:
                self.stderr.write(f'  Line {line_num}: {dr_str}')

        # Cross-check with database
        matched = []
        mismatches = []
        missing = []
        multiple_resources = []
        empty_status_updates = []

        for dr_number, new_status in updates:
            # Get all records with this DR number
            records = Deficiency.objects.filter(deficiency_number=dr_number)

            if not records.exists():
                missing.append(dr_number)
                continue

            if records.count() > 1:
                # Multiple records with same DR number (different resources)
                resources = list(records.values_list('resource', flat=True))
                multiple_resources.append({
                    'dr_number': dr_number,
                    'count': records.count(),
                    'resources': resources
                })

                if update_all:
                    # Update ALL records with this DR number
                    for record in records:
                        # Check if status is empty/NULL for fill-empty-only mode
                        if fill_empty_only:
                            if not record.status or record.status.strip() == '':
                                empty_status_updates.append({
                                    'dr_number': dr_number,
                                    'new': new_status,
                                    'obj': record,
                                    'resource': record.resource
                                })
                            else:
                                matched.append(dr_number)
                        elif record.status != new_status:
                            mismatches.append({
                                'dr_number': dr_number,
                                'current': record.status,
                                'new': new_status,
                                'obj': record,
                                'resource': record.resource
                            })
                        else:
                            matched.append(dr_number)
                else:
                    # Skip - don't update multiple records without --update-all flag
                    for record in records:
                        if record.status == new_status:
                            matched.append(dr_number)
                    continue
            else:
                # Single record - normal processing
                deficiency = records.first()
                current_status = deficiency.status

                # Check if status is empty/NULL for fill-empty-only mode
                if fill_empty_only:
                    if not current_status or current_status.strip() == '':
                        empty_status_updates.append({
                            'dr_number': dr_number,
                            'new': new_status,
                            'obj': deficiency,
                            'resource': deficiency.resource
                        })
                    else:
                        matched.append(dr_number)
                elif current_status != new_status:
                    mismatches.append({
                        'dr_number': dr_number,
                        'current': current_status,
                        'new': new_status,
                        'obj': deficiency,
                        'resource': deficiency.resource
                    })
                else:
                    matched.append(dr_number)

        # Display results
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'Already matched: {len(set(matched))}')
        if fill_empty_only:
            self.stdout.write(f'Empty statuses to fill: {len(empty_status_updates)}')
        self.stdout.write(f'Status mismatches: {len(mismatches)}')
        self.stdout.write(f'Not found in DB: {len(missing)}')
        if multiple_resources:
            self.stdout.write(self.style.WARNING(f'Multiple resources (same DR#): {len(multiple_resources)}'))
        self.stdout.write('='*60 + '\n')

        if missing:
            self.stderr.write(self.style.WARNING('DRs NOT found in database:'))
            for dr in missing:
                self.stderr.write(f'  DR#{dr}')

        if multiple_resources and not update_all:
            self.stderr.write(self.style.WARNING('DRs with MULTIPLE resources (use --update-all to update all):'))
            for m in multiple_resources:
                self.stderr.write(f'  DR#{m["dr_number"]}: {m["count"]} records ({", ".join(m["resources"])})')

        if empty_status_updates:
            self.stdout.write(self.style.SUCCESS('DRs with EMPTY/NULL status (ready to fill):'))
            for m in empty_status_updates:
                self.stdout.write(f'  DR#{m["dr_number"]} [{m["resource"]}]: "(empty)" → "{m["new"]}"')

        if mismatches and not fill_empty_only:
            self.stdout.write(self.style.WARNING('Status MISMATCHES found:'))
            for m in mismatches:
                resource_str = f' [{m["resource"]}]' if 'resource' in m else ''
                self.stdout.write(
                    f'  DR#{m["dr_number"]}{resource_str}: "{m["current"]}" → "{m["new"]}"'
                )

        # Apply updates
        if not dry_run and (mismatches or empty_status_updates):
            updates_to_apply = mismatches if not fill_empty_only else empty_status_updates

            # Interactive mode for fill-empty-only
            if fill_empty_only:
                self.stdout.write('\n' + '='*60)
                self.stdout.write('INTERACTIVE MODE: Review each update')
                self.stdout.write('='*60)
                self.stdout.write('Options for each DR:')
                self.stdout.write('  y = Yes, update this record')
                self.stdout.write('  n = No, skip this record')
                self.stdout.write('  a = Yes to ALL remaining')
                self.stdout.write('  q = Quit')
                self.stdout.write('='*60)

                updated = 0
                skipped = 0
                update_all_remaining = False

                with transaction.atomic():
                    for m in updates_to_apply:
                        if update_all_remaining:
                            m['obj'].status = m['new']
                            m['obj'].save()
                            resource_str = f' [{m["resource"]}]' if 'resource' in m else ''
                            self.stdout.write(self.style.SUCCESS(f'  ✓ Updated DR#{m["dr_number"]}{resource_str} to "{m["new"]}"'))
                            updated += 1
                        else:
                            resource_str = f' [{m["resource"]}]' if 'resource' in m else ''
                            self.stdout.write(f'\nDR#{m["dr_number"]}{resource_str}: "(empty)" → "{m["new"]}"')

                            choice = input('Update this record? (y/n/a/q): ').strip().lower()

                            if choice == 'y':
                                m['obj'].status = m['new']
                                m['obj'].save()
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated'))
                                updated += 1
                            elif choice == 'a':
                                update_all_remaining = True
                                m['obj'].status = m['new']
                                m['obj'].save()
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated (remaining will auto-update)'))
                                updated += 1
                            elif choice == 'n':
                                self.stdout.write(self.style.WARNING('  ✗ Skipped'))
                                skipped += 1
                            elif choice == 'q':
                                self.stdout.write(self.style.WARNING('\nStopped by user'))
                                break
                else:
                    # Loop completed without break
                    self.stdout.write(self.style.SUCCESS(f'\nCompleted! Updated: {updated}, Skipped: {skipped}'))
                return
            else:
                # Non-interactive mode - update all
                self.stdout.write('\nUpdating database...')
                with transaction.atomic():
                    for m in updates_to_apply:
                        m['obj'].status = m['new']
                        m['obj'].save()
                        resource_str = f' [{m["resource"]}]' if 'resource' in m else ''
                        self.stdout.write(self.style.SUCCESS(f'  Updated DR#{m["dr_number"]}{resource_str} to "{m["new"]}"'))

                self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {len(updates_to_apply)} records'))
        elif dry_run and (mismatches or empty_status_updates):
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No actual updates performed'))

        if not mismatches and not missing and not empty_status_updates:
            self.stdout.write(self.style.SUCCESS('All DRs are already in sync!'))

"""
Django management command to sync DR with multiple fields from separate text files.

Files (all must have same number of lines):
1. dr_numbers.txt    - DR numbers (one per line)
2. cleared_dates.txt - Cleared dates (one per line, empty for none)
3. due_dates.txt     - Due dates (one per line)
4. statuses.txt      - Statuses (one per line)

Files are matched by line position.

Usage:
    python manage.py sync_dr_full --numbers dr_numbers.txt --cleared cleared_dates.txt --due due_dates.txt --statuses statuses.txt
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from apps.deficiencies.models import Deficiency
from apps.deficiencies.utility import normalize_date


class Command(BaseCommand):
    help = 'Sync DR with multiple fields from separate text files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--numbers',
            type=str,
            required=True,
            help='Path to text file containing DR numbers'
        )
        parser.add_argument(
            '--cleared',
            type=str,
            required=True,
            help='Path to text file containing Cleared Dates'
        )
        parser.add_argument(
            '--due',
            type=str,
            required=True,
            help='Path to text file containing Due Dates'
        )
        parser.add_argument(
            '--statuses',
            type=str,
            required=True,
            help='Path to text file containing Statuses'
        )
        parser.add_argument(
            '--update-all',
            action='store_true',
            help='Update ALL records with same DR number (including different resources)'
        )
        parser.add_argument(
            '--fill-empty-only',
            action='store_true',
            help='Only update fields that are NULL/empty in database (interactive mode)'
        )

    def read_file(self, file_path):
        """Read file and return list of lines (preserves empty lines as empty strings)"""
        try:
            with open(file_path, 'r') as f:
                raw_lines = f.readlines()
                total_lines = len(raw_lines)

                lines = []
                skipped_comments = 0
                in_data_range = False  # Flag for <start>/<end> markers

                for line in raw_lines:
                    stripped = line.strip()

                    # Check for <start> marker
                    if stripped == '<start>':
                        in_data_range = True
                        continue

                    # Check for <end> marker
                    if stripped == '<end>':
                        in_data_range = False
                        continue

                    # Skip lines before <start> or after <end>
                    if not in_data_range:
                        if stripped.startswith('#'):
                            skipped_comments += 1
                        continue

                    # Skip comment lines within data range
                    if stripped.startswith('#'):
                        skipped_comments += 1
                        continue

                    # Empty line becomes empty string
                    lines.append(stripped if stripped else '')

                filename = file_path.split("/")[-1].split("\\")[-1]
                self.stdout.write(f'  {filename}: {total_lines} total lines, {len(lines)} data lines (using <start>/<end> range)')

                return lines
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
            return None

    def parse_updates(self, numbers, cleared_dates, due_dates, statuses):
        """Parse and validate the input data"""
        updates = []
        errors = []

        for i, (dr_num_str, cleared_date, due_date, status) in enumerate(
            zip(numbers, cleared_dates, due_dates, statuses), 1
        ):
            dr_num_str = dr_num_str.strip('# ')
            cleared_date = cleared_date.strip()
            due_date = due_date.strip()
            status = status.strip()

            try:
                dr_number = int(dr_num_str)
                updates.append({
                    'line': i,
                    'dr_number': dr_number,
                    'cleared_date': cleared_date if cleared_date else None,  # Keep original for normalization
                    'due_date': due_date if due_date else None,           # Keep original for normalization
                    'status': status
                })
            except ValueError:
                errors.append((i, dr_num_str))

        return updates, errors

    def compare_with_db(self, updates, update_all, fill_empty_only=False):
        """Compare updates with database and categorize"""
        matched = []
        changes = []
        missing = []
        multiple_resources = []

        for update in updates:
            dr_number = update['dr_number']
            records = Deficiency.objects.filter(deficiency_number=dr_number)

            if not records.exists():
                missing.append(update)
                continue

            if records.count() > 1:
                resources = list(records.values_list('resource', flat=True))
                multiple_resources.append({
                    'update': update,
                    'count': records.count(),
                    'resources': resources
                })

                if update_all:
                    for record in records:
                        change = self.check_for_changes(record, update, fill_empty_only)
                        if change:
                            changes.append(change)
                        else:
                            matched.append(update)
                else:
                    # Check if any record matches - if so, consider matched
                    for record in records:
                        if not self.check_for_changes(record, update, fill_empty_only):
                            matched.append(update)
                            break
                    continue
            else:
                # Single record
                record = records.first()
                change = self.check_for_changes(record, update, fill_empty_only)
                if change:
                    changes.append(change)
                else:
                    matched.append(update)

        return matched, changes, missing, multiple_resources

    def check_for_changes(self, record, update, fill_empty_only=False):
        """Check if record has any differences from update"""
        differences = {}
        warnings = []

        # Store original values for saving
        original_cleared = update['cleared_date']
        original_due = update['due_date']

        # Check status (only if field is empty when fill_empty_only is True)
        if fill_empty_only:
            # Only check if status is empty/NULL
            if not record.status or str(record.status).strip() == '':
                if update['status'] and update['status'].strip():
                    differences['status'] = {
                        'old': '(empty)',
                        'new': update['status']
                    }
            # Skip checking non-empty fields
        else:
            # Normal mode: check all differences
            if record.status != update['status']:
                differences['status'] = {
                    'old': record.status,
                    'new': update['status']
                }

        # Check due_date (only if field is empty when fill_empty_only is True)
        if fill_empty_only:
            # Only check if due_date is empty/NULL
            if not record.due_date:
                if original_due and original_due.strip():
                    differences['due_date'] = {
                        'old': '(empty)',
                        'new': original_due
                    }
        else:
            # Normal mode: check all differences
            old_due = str(record.due_date) if record.due_date else ''
            new_due = original_due or ''
            if new_due:
                normalized = normalize_date(new_due)
                if normalized and hasattr(normalized, 'strftime'):
                    new_due_normalized = normalized.strftime('%Y-%m-%d')
                else:
                    new_due_normalized = new_due
            else:
                new_due_normalized = ''

            if old_due != new_due_normalized:
                differences['due_date'] = {
                    'old': old_due,
                    'new': original_due or '(empty)'
                }

        # Check cleared_date (only if field is empty when fill_empty_only is True)
        if fill_empty_only:
            # Only check if cleared_date is empty/NULL
            if not record.cleared_date:
                if original_cleared and original_cleared.strip():
                    differences['cleared_date'] = {
                        'old': '(empty)',
                        'new': original_cleared
                    }
        else:
            # Normal mode: check all differences
            old_cleared = str(record.cleared_date) if record.cleared_date else ''
            new_cleared = original_cleared or ''
            if new_cleared:
                normalized = normalize_date(new_cleared)
                if normalized and hasattr(normalized, 'strftime'):
                    new_cleared_normalized = normalized.strftime('%Y-%m-%d')
                else:
                    new_cleared_normalized = new_cleared
            else:
                new_cleared_normalized = ''

            if old_cleared != new_cleared_normalized:
                differences['cleared_date'] = {
                    'old': old_cleared,
                    'new': original_cleared or '(empty)'
                }

        # Validation: Check if status is Cleared but no cleared_date
        new_status = update['status']
        has_cleared_date = original_cleared and original_cleared.strip()

        if new_status == 'Cleared' and not has_cleared_date:
            warnings.append('Status is Cleared but no ClearedDate provided')
        elif new_status != 'Cleared' and has_cleared_date:
            warnings.append(f'ClearedDate provided but status is {new_status} (should be empty)')

        if differences:
            return {
                'dr_number': update['dr_number'],
                'obj': record,
                'resource': record.resource,
                'differences': differences,
                'warnings': warnings,
                'original_cleared': original_cleared,
                'original_due': original_due
            }
        return None

    def display_changes(self, changes):
        """Display the changes in a readable format"""
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.WARNING('CHANGES NEEDED:'))
        self.stdout.write('='*70)

        for i, change in enumerate(changes, 1):
            self.stdout.write(f'\n[{i}] DR#{change["dr_number"]} [{change["resource"]}]:')
            for field, diff in change['differences'].items():
                old_val = diff['old'] or '(empty)'
                new_val = diff['new'] or '(empty)'
                self.stdout.write(f'    {field}: "{old_val}" → "{new_val}"')

            # Display warnings if any
            if 'warnings' in change and change['warnings']:
                for warning in change['warnings']:
                    self.stdout.write(self.style.ERROR(f'    ⚠️  WARNING: {warning}'))

    def ask_user_choice(self, changes):
        """Ask user how to proceed with changes"""
        self.stdout.write('\n' + '='*70)
        self.stdout.write('Options:')
        self.stdout.write('  1. Update ALL changes')
        self.stdout.write('  2. Update ONE BY ONE (confirm each)')
        self.stdout.write('  3. Cancel (no changes)')
        self.stdout.write('='*70)

        while True:
            choice = input('\nEnter choice (1/2/3): ').strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            self.stderr.write(self.style.ERROR('Invalid choice. Enter 1, 2, or 3.'))

    def ask_individual_change(self, change, index, total):
        """Ask user about individual change"""
        self.stdout.write(f'\n[{index}/{total}] DR#{change["dr_number"]} [{change["resource"]}]:')
        for field, diff in change['differences'].items():
            old_val = diff['old'] or '(empty)'
            new_val = diff['new'] or '(empty)'
            self.stdout.write(f'  {field}: "{old_val}" → "{new_val}"')

        # Display warnings if any
        if 'warnings' in change and change['warnings']:
            for warning in change['warnings']:
                self.stdout.write(self.style.ERROR(f'  ⚠️  WARNING: {warning}'))

        while True:
            choice = input('Update this record? (y/n/q to quit): ').strip().lower()
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            elif choice == 'q':
                return 'quit'

    def apply_updates(self, changes, mode):
        """Apply updates based on mode"""
        if mode == 1:
            # Update all
            self.stdout.write(self.style.SUCCESS(f'\nUpdating ALL {len(changes)} records...'))
            with transaction.atomic():
                for change in changes:
                    record = change['obj']
                    if 'status' in change['differences']:
                        record.status = change['differences']['status']['new']
                    if 'due_date' in change['differences']:
                        new_due = change['original_due']
                        if new_due:
                            record.due_date = normalize_date(new_due)
                        else:
                            record.due_date = None
                    if 'cleared_date' in change['differences']:
                        new_cleared = change['original_cleared']
                        if new_cleared:
                            record.cleared_date = normalize_date(new_cleared)
                        else:
                            record.cleared_date = None
                    record.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Updated DR#{record.deficiency_number} [{record.resource}]'))
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {len(changes)} records'))

        elif mode == 2:
            # Update one by one
            updated = 0
            skipped = 0
            with transaction.atomic():
                for i, change in enumerate(changes, 1):
                    result = self.ask_individual_change(change, i, len(changes))
                    if result == True:
                        record = change['obj']
                        if 'status' in change['differences']:
                            record.status = change['differences']['status']['new']
                        if 'due_date' in change['differences']:
                            new_due = change['original_due']
                            if new_due:
                                record.due_date = normalize_date(new_due)
                            else:
                                record.due_date = None
                        if 'cleared_date' in change['differences']:
                            new_cleared = change['original_cleared']
                            if new_cleared:
                                record.cleared_date = normalize_date(new_cleared)
                            else:
                                record.cleared_date = None
                        record.save()
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated DR#{record.deficiency_number} [{record.resource}]'))
                        updated += 1
                    elif result == False:
                        self.stdout.write(self.style.WARNING(f'  ✗ Skipped DR#{change["dr_number"]}'))
                        skipped += 1
                    elif result == 'quit':
                        self.stdout.write(self.style.WARNING('\nStopped by user'))
                        break

            self.stdout.write(self.style.SUCCESS(f'\nUpdated: {updated}, Skipped: {skipped}'))

    def handle(self, *args, **options):
        numbers_file = options['numbers']
        cleared_file = options['cleared']
        due_file = options['due']
        statuses_file = options['statuses']
        update_all = options['update_all']
        fill_empty_only = options['fill_empty_only']

        if fill_empty_only:
            self.stdout.write(self.style.WARNING('FILL EMPTY ONLY MODE: Only updating NULL/empty fields'))

        self.stdout.write('Reading input files...')

        # Read all files
        numbers = self.read_file(numbers_file)
        cleared_dates = self.read_file(cleared_file)
        due_dates = self.read_file(due_file)
        statuses = self.read_file(statuses_file)

        if None in [numbers, cleared_dates, due_dates, statuses]:
            return

        # Validate line counts
        line_count = len(numbers)
        if len(cleared_dates) != line_count or len(due_dates) != line_count or len(statuses) != line_count:
            self.stderr.write(self.style.ERROR('File length mismatch!'))
            self.stderr.write(f'  Numbers: {line_count} lines')
            self.stderr.write(f'  Cleared Dates: {len(cleared_dates)} lines')
            self.stderr.write(f'  Due Dates: {len(due_dates)} lines')
            self.stderr.write(f'  Statuses: {len(statuses)} lines')
            self.stderr.write('All files must have the same number of lines.')
            return

        self.stdout.write(f'Processing {line_count} records...')

        # Parse updates
        updates, errors = self.parse_updates(numbers, cleared_dates, due_dates, statuses)

        if errors:
            self.stderr.write(self.style.WARNING(f'Could not parse {len(errors)} DR numbers:'))
            for line_num, dr_str in errors:
                self.stderr.write(f'  Line {line_num}: {dr_str}')

        # Compare with database
        matched, changes, missing, multiple_resources = self.compare_with_db(updates, update_all, fill_empty_only)

        # Display summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(f'Already matched: {len(matched)}')
        self.stdout.write(f'Changes needed: {len(changes)}')
        self.stdout.write(f'Not found in DB: {len(missing)}')
        if multiple_resources:
            self.stdout.write(self.style.WARNING(f'Multiple resources: {len(multiple_resources)}'))
        self.stdout.write('='*70)

        if missing:
            self.stderr.write(self.style.WARNING('\nDRs NOT found in database:'))
            for m in missing:
                self.stderr.write(f'  Line {m["line"]}: DR#{m["dr_number"]}')

        if multiple_resources and not update_all:
            self.stderr.write(self.style.WARNING('\nDRs with MULTIPLE resources (use --update-all to update all):'))
            for m in multiple_resources:
                self.stderr.write(f'  DR#{m["update"]["dr_number"]}: {m["count"]} records ({", ".join(m["resources"])})')

        if not changes:
            self.stdout.write(self.style.SUCCESS('\nAll DRs are already in sync!'))
            return

        # Display changes
        self.display_changes(changes)

        # Ask user what to do
        choice = self.ask_user_choice(changes)

        if choice == 1:
            self.apply_updates(changes, mode=1)
        elif choice == 2:
            self.apply_updates(changes, mode=2)
        elif choice == 3:
            self.stdout.write(self.style.WARNING('\nCancelled. No changes applied.'))

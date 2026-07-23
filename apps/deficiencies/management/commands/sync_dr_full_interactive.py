"""
Django management command to sync DR with interactive editing capability.

Files (all must have same number of lines):
1. dr_numbers.txt    - DR numbers (one per line)
2. cleared_dates.txt - Cleared dates (one per line, empty for none)
3. due_dates.txt     - Due dates (one per line)
4. statuses.txt      - Statuses (one per line)
5. raised_dates.txt  - Raised dates (one per line, optional, empty for none)

Supported date formats:
- YYYY-MM-DD (2025-01-15)
- DD-Mon-YYYY (15-Jan-2025)
- DD Month YYYY (15 January 2025)
- Month DD YYYY HH:MM AM/PM (June 15 2026 04:00 PM)

Usage:
    python manage.py sync_dr_full_interactive --numbers dr_numbers.txt --cleared cleared_dates.txt --due due_dates.txt --statuses statuses.txt --raised raised_dates.txt
"""

import logging
from collections import defaultdict
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.deficiencies.models import Deficiency


def normalize_date_for_django(date_str):
    """Parse various date formats into strict YYYY-MM-DD strings.

    Supports formats like:
    - YYYY-MM-DD (2025-01-15)
    - DD-Mon-YYYY (15-Jan-2025)
    - DD Month YYYY (15 January 2025)
    - Month DD YYYY HH:MM AM/PM (June 15 2026 04:00 PM)
    """
    if not date_str or str(date_str).strip().lower() in ["(empty)", "none", ""]:
        return None

    # Remove any rogue smart quotes or spaces
    clean_str = str(date_str).strip('"\' ')

    # Supported formats - order matters for parsing
    # Try strict formats with time first (more specific)
    formats_with_time = (
        "%B %d %Y %I:%M %p",   # June 15 2026 04:00 PM
        "%B %d %Y %I:%M%p",    # June 15 2026 04:00PM (no space before AM/PM)
        "%b %d %Y %I:%M %p",   # Jan 15 2026 04:00 PM
        "%b %d %Y %I:%M%p",    # Jan 15 2026 04:00PM
        "%B %d %Y %I:%M:%S %p", # June 15 2026 04:00:00 PM
        "%B %d %Y %H:%M",      # June 15 2026 16:00 (24-hour format)
    )

    # Date-only formats
    formats_date_only = (
        "%Y-%m-%d",    # 2025-01-15
        "%d-%b-%Y",    # 15-Jan-2025
        "%d-%b-%y",    # 15-Jan-25
        "%d %b %Y",    # 15 Jan 2025
        "%d %B %Y",    # 15 January 2025
        "%B %d %Y",    # January 15 2025 / June 15 2026
        "%b %d %Y",    # Jan 15 2025
    )

    # Try formats with time first
    for fmt in formats_with_time:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Then try date-only formats
    for fmt in formats_date_only:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"'{date_str}' value has an invalid date format.")


class Command(BaseCommand):
    help = 'Sync DR with interactive editing capability'

    def add_arguments(self, parser):
        parser.add_argument('--numbers', type=str, required=True, help='Path to DR numbers file')
        parser.add_argument('--cleared', type=str, required=True, help='Path to Cleared Dates file')
        parser.add_argument('--due', type=str, required=True, help='Path to Due Dates file')
        parser.add_argument('--statuses', type=str, required=True, help='Path to Statuses file')
        parser.add_argument('--raised', type=str, required=False, default=None, help='Path to Raised Dates file (optional)')
        parser.add_argument('--update-all', action='store_true', help='Update ALL records with same DR number')

    def read_file(self, file_path):
        """Read file and return list of lines"""
        try:
            with open(file_path, 'r') as f:
                lines = []
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
                    lines.append(stripped if stripped else '')
                return lines
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
            return None

    def handle(self, *args, **options):
        # Configure logging to output to log.txt
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('log.txt')
            ]
        )
        logging.info("=== STARTED DR SYNC PROCESS ===")

        numbers_file = options['numbers']
        cleared_file = options['cleared']
        due_file = options['due']
        statuses_file = options['statuses']
        raised_file = options['raised']
        update_all = options['update_all']

        # Read files
        numbers = self.read_file(numbers_file)
        cleared_dates = self.read_file(cleared_file)
        due_dates = self.read_file(due_file)
        statuses = self.read_file(statuses_file)
        raised_dates = self.read_file(raised_file) if raised_file else None

        if None in [numbers, cleared_dates, due_dates, statuses]:
            logging.error("Failed to read one or more input files.")
            return

        # Validate line counts
        line_count = len(numbers)
        if len(cleared_dates) != line_count or len(due_dates) != line_count or len(statuses) != line_count:
            msg = 'File length mismatch!'
            self.stderr.write(self.style.ERROR(msg))
            logging.error(msg)
            return

        # If raised dates file is provided, validate its line count
        if raised_dates is not None and len(raised_dates) != line_count:
            msg = 'Raised dates file length mismatch!'
            self.stderr.write(self.style.ERROR(msg))
            logging.error(msg)
            return

        self.stdout.write(f'Processing {line_count} records...\n')
        logging.info(f"Processing {line_count} records...")

        # Build update list
        updates = []
        if raised_dates is not None:
            for i, (dr_num_str, cleared_date, due_date, status, raised_date) in enumerate(
                zip(numbers, cleared_dates, due_dates, statuses, raised_dates), 1
            ):
                try:
                    dr_number = int(dr_num_str.strip('# '))
                    updates.append({
                        'line': i,
                        'dr_number': dr_number,
                        'cleared_date': cleared_date if cleared_date else None,
                        'due_date': due_date if due_date else None,
                        'status': status,
                        'raised_date': raised_date if raised_date else None
                    })
                except ValueError:
                    continue
        else:
            for i, (dr_num_str, cleared_date, due_date, status) in enumerate(
                zip(numbers, cleared_dates, due_dates, statuses), 1
            ):
                try:
                    dr_number = int(dr_num_str.strip('# '))
                    updates.append({
                        'line': i,
                        'dr_number': dr_number,
                        'cleared_date': cleared_date if cleared_date else None,
                        'due_date': due_date if due_date else None,
                        'status': status,
                        'raised_date': None
                    })
                except ValueError:
                    continue

        # Get database records
        pending_updates = []
        missing = []
        multiple_resources = []

        # 1. Get a list of all DR numbers we want to look up
        dr_numbers = [u['dr_number'] for u in updates]

        # 2. Fetch ALL matching records in ONE single database query
        all_records = Deficiency.objects.filter(deficiency_number__in=dr_numbers)

        # 3. Group the records by DR number in memory
        records_by_dr = defaultdict(list)
        for record in all_records:
            records_by_dr[record.deficiency_number].append(record)

        # 4. Now process your updates using the pre-loaded memory dictionary
        for update in updates:
            dr_number = update['dr_number']
            matched_records = records_by_dr.get(dr_number, [])

            if not matched_records:
                missing.append(dr_number)
                continue

            if len(matched_records) > 1:
                resources = [r.resource for r in matched_records]
                multiple_resources.append({
                    'dr_number': dr_number,
                    'count': len(matched_records),
                    'resources': resources
                })
                if update_all:
                    for record in matched_records:
                        pending_updates.append({
                            'update': update,
                            'record': record,
                            'resource': record.resource
                        })
                continue

            # Single record
            record = matched_records[0]
            pending_updates.append({
                'update': update,
                'record': record,
                'resource': record.resource
            })

        # Show missing
        if missing:
            warning_msg = f'DRs NOT found in database: {len(missing)}'
            self.stderr.write(self.style.WARNING(warning_msg))
            logging.warning(warning_msg)
            for dr in missing[:10]:
                self.stderr.write(f'  DR#{dr}')

        # Show multiple resources
        if multiple_resources and not update_all:
            warning_msg = f'\nDRs with multiple resources (use --update-all):'
            self.stderr.write(self.style.WARNING(warning_msg))
            logging.warning("Found DRs with multiple resources. Not updating them because --update-all was not passed.")
            for m in multiple_resources[:10]:
                self.stderr.write(f'  DR#{m["dr_number"]}: {m["count"]} records ({", ".join(m["resources"])})')

        # Ask user about processing order
        process_changes_first = self.ask_processing_order()

        # Split updates into two groups if requested
        if process_changes_first:
            auto_updates, interactive_updates = self.split_updates_by_changes(pending_updates)
            self.stdout.write(self.style.SUCCESS(f'\nRecords for AUTO update: {len(auto_updates)}'))
            self.stdout.write(self.style.SUCCESS(f'Records for INTERACTIVE review: {len(interactive_updates)}'))

            # Process safe changes AUTOMATICALLY first
            self.process_automatic_updates(auto_updates, phase_name="AUTO PHASE")

            # Then process empty due_dates or no-changes interactively
            if interactive_updates:
                continue_processing = input('\nContinue with interactive manual review phase? (yes/no): ').strip().lower()
                if continue_processing in ['yes', 'y']:
                    self.process_interactive_updates(interactive_updates, phase_name="INTERACTIVE PHASE")
        else:
            # Process all interactively in original order
            self.process_interactive_updates(pending_updates)

    def ask_processing_order(self):
        """Ask user if they want to process records with changes first"""
        while True:
            self.stdout.write('\nPROCESSING ORDER:')
            self.stdout.write('  1. Process records WITH changes first (recommended)')
            self.stdout.write('  2. Process all records in original order')
            self.stdout.write('='*70)

            choice = input('\nEnter choice (1-2): ').strip()

            if choice == '1':
                return True
            elif choice == '2':
                return False
            else:
                self.stderr.write(self.style.ERROR('Invalid choice. Please enter 1 or 2.'))

    def split_updates_by_changes(self, pending_updates):
        """Split updates into auto-processable and interactive"""
        auto_updates = []
        interactive_updates = []

        for item in pending_updates:
            record = item['record']
            update = item['update']

            due_file = update.get('due_date')
            is_due_empty = not due_file or str(due_file).strip().lower() in ['(empty)', 'none', '']

            # If due_date is empty, it MUST go to the interactive phase so you can manually fix it
            if is_due_empty:
                interactive_updates.append(item)
            elif self.has_differences(record, update):
                auto_updates.append(item)
            else:
                interactive_updates.append(item)

        return auto_updates, interactive_updates

    def has_differences(self, record, update):
        """Check if there are differences between database and file values"""
        # Check status difference
        status_db = record.status or '(empty)'
        status_file = update.get('status') or '(empty)'
        if status_db != status_file:
            return True

        # Check due_date difference
        due_db = str(record.due_date).split(' ')[0] if record.due_date else '(empty)'
        due_file = update.get('due_date') or '(empty)'
        if due_file != '(empty)' and due_db != due_file:
            return True

        # Check cleared_date difference
        cleared_db = str(record.cleared_date).split(' ')[0] if record.cleared_date else '(empty)'
        cleared_file = update.get('cleared_date') or '(empty)'
        if cleared_file != '(empty)' and cleared_db != cleared_file:
            return True

        # Check raised_date difference
        raised_db = str(record.raised_date).split(' ')[0] if record.raised_date else '(empty)'
        raised_file = update.get('raised_date') or '(empty)'
        if raised_file != '(empty)' and raised_db != raised_file:
            return True

        return False

    def process_interactive_updates(self, pending_updates, phase_name=None):
        """Process updates one by one with preview and user input"""
        if not pending_updates:
            self.stdout.write(self.style.SUCCESS('\nNo updates to process.'))
            return

        phase_info = f' - {phase_name}' if phase_name else ''
        self.stdout.write(self.style.SUCCESS(f'\nFound {len(pending_updates)} records to update{phase_info}\n'))
        self.stdout.write('='*70)

        updated_count = 0
        skipped_count = 0

        for i, item in enumerate(pending_updates, 1):
            record = item['record']
            update = item['update']

            phase_display = f' [{phase_name}] ' if phase_name else ' '
            self.stdout.write(f'\n[{i}/{len(pending_updates)}]{phase_display}Processing DR#{update["dr_number"]} [{item["resource"]}]:')
            self.stdout.write('='*70)

            # Show comparison preview
            changes_found = self.show_comparison_preview(record, update)

            # Check if this record is here because it has an empty due_date
            due_file = update.get('due_date')
            is_due_empty = not due_file or str(due_file).strip().lower() in ['(empty)', 'none', '']

            if not changes_found and not is_due_empty:
                self.stdout.write(self.style.WARNING('No changes detected - skipping'))
                skipped_count += 1
                continue

            if is_due_empty:
                self.stdout.write(self.style.WARNING('⚠ WARNING: This record is missing a Due Date. You must enter one manually.'))

            # Get user action
            action = self.get_user_action()

            if action == 'skip':
                self.stdout.write(self.style.WARNING('Skipped'))
                logging.info(f"DR#{update['dr_number']}: Skipped interactively.")
                skipped_count += 1
                continue
            elif action == 'manual':
                # Get manual values from user
                self.get_manual_values(update)
                # Apply the update with manual values
                if self.apply_single_update(record, update):
                    updated_count += 1
            elif action == 'apply':
                # Apply the update as-is from file
                if self.apply_single_update(record, update):
                    updated_count += 1
            elif action == 'exit':
                self.stdout.write(self.style.WARNING('Exiting early...'))
                logging.info("User exited interactive mode early.")
                break

        # Show summary
        summary = f'Summary: {updated_count} updated, {skipped_count} skipped'
        self.stdout.write('\n' + '='*70)
        self.stdout.write(summary)
        self.stdout.write('='*70)
        logging.info(f"Interactive Phase {summary}")

    def show_comparison_preview(self, record, update):
        """Show comparison between database values and file values"""
        changes_found = False

        self.stdout.write('\n--- COMPARISON PREVIEW ---')

        # Show status comparison
        status_db = record.status or '(empty)'
        status_file = update.get('status') or '(empty)'
        if status_db != status_file:
            self.stdout.write(f'status:       "{status_db}" → "{status_file}"')
            changes_found = True
        else:
            self.stdout.write(f'status:       "{status_db}" (no change)')

        # Show due_date comparison
        due_db = str(record.due_date).split(' ')[0] if record.due_date else '(empty)'
        due_file = update.get('due_date') or '(empty)'
        if due_file != '(empty)' and due_db != due_file:
            self.stdout.write(f'due_date:     "{due_db}" → "{due_file}"')
            changes_found = True
        else:
            self.stdout.write(f'due_date:     "{due_db}" (no change)')

        # Show cleared_date comparison
        cleared_db = str(record.cleared_date).split(' ')[0] if record.cleared_date else '(empty)'
        cleared_file = update.get('cleared_date') or '(empty)'
        if cleared_file != '(empty)' and cleared_db != cleared_file:
            self.stdout.write(f'cleared_date: "{cleared_db}" → "{cleared_file}"')
            changes_found = True
        else:
            self.stdout.write(f'cleared_date: "{cleared_db}" (no change)')

        # Show raised_date comparison (if provided)
        raised_db = str(record.raised_date).split(' ')[0] if record.raised_date else '(empty)'
        raised_file = update.get('raised_date') or '(empty)'
        if raised_file != '(empty)' and raised_db != raised_file:
            self.stdout.write(f'raised_date:  "{raised_db}" → "{raised_file}"')
            changes_found = True
        else:
            self.stdout.write(f'raised_date:  "{raised_db}" (no change)')

        self.stdout.write('='*70)
        return changes_found

    def process_automatic_updates(self, pending_updates, phase_name=None):
        """Process updates automatically without user prompts"""
        if not pending_updates:
            self.stdout.write(self.style.SUCCESS('\nNo automatic updates to process.'))
            return

        phase_info = f' - {phase_name}' if phase_name else ''
        self.stdout.write(self.style.SUCCESS(f'\nAuto-processing {len(pending_updates)} records{phase_info}\n'))
        self.stdout.write('='*70)

        updated_count = 0
        error_count = 0

        for i, item in enumerate(pending_updates, 1):
            record = item['record']
            update = item['update']

            phase_display = f' [{phase_name}] ' if phase_name else ' '
            self.stdout.write(f'\n[{i}/{len(pending_updates)}]{phase_display}Processing DR#{update["dr_number"]} [{item["resource"]}]:')
            self.stdout.write('='*70)

            # Show preview
            self.show_comparison_preview(record, update)

            # Apply automatically
            if self.apply_single_update(record, update):
                updated_count += 1
            else:
                error_count += 1

        # Show summary
        summary = f'Auto-update Summary: {updated_count} updated, {error_count} errors'
        self.stdout.write('\n' + '='*70)
        self.stdout.write(summary)
        self.stdout.write('='*70)
        logging.info(f"Automatic Phase {summary}")

    def get_user_action(self):
        """Get user action for current record"""
        while True:
            self.stdout.write('\nACTION:')
            self.stdout.write('  1. Apply file values')
            self.stdout.write('  2. Enter manual values')
            self.stdout.write('  3. Skip this record')
            self.stdout.write('  4. Exit (stop processing)')
            self.stdout.write('='*70)

            choice = input('\nEnter choice (1-4): ').strip()

            if choice == '1':
                return 'apply'
            elif choice == '2':
                return 'manual'
            elif choice == '3':
                return 'skip'
            elif choice == '4':
                return 'exit'
            else:
                self.stderr.write(self.style.ERROR('Invalid choice. Please enter 1-4.'))

    def get_manual_values(self, update):
        """Get manual values from user for the current update"""
        self.stdout.write('\n--- ENTER MANUAL VALUES ---')

        # Get manual values with current/file values as defaults
        new_status = input(f'Status [{update.get("status") or "(empty)"}]: ').strip()
        new_due = input(f'Due Date [{update.get("due_date") or "(empty)"}]: ').strip()
        new_cleared = input(f'Cleared Date [{update.get("cleared_date") or "(empty)"}]: ').strip()
        new_raised = input(f'Raised Date [{update.get("raised_date") or "(empty)"}]: ').strip()

        # Update the values if user provided new ones
        if new_status:
            update['status'] = new_status
        if new_due:
            update['due_date'] = new_due
        if new_cleared:
            update['cleared_date'] = new_cleared
        if new_raised:
            update['raised_date'] = new_raised

        self.stdout.write('\n--- UPDATED VALUES ---')
        self.stdout.write(f'status:       {update.get("status") or "(empty)"}')
        self.stdout.write(f'due_date:     {update.get("due_date") or "(empty)"}')
        self.stdout.write(f'cleared_date: {update.get("cleared_date") or "(empty)"}')
        self.stdout.write(f'raised_date:  {update.get("raised_date") or "(empty)"}')

    def apply_single_update(self, record, update):
        """Apply a single update to the database wrapped in an atomic transaction"""
        dr_num = update['dr_number']
        try:
            with transaction.atomic():
                update_kwargs = {}

                # Apply status
                if update.get('status'):
                    update_kwargs['status'] = update['status']

                # Check for empty Due Date constraint
                due_file = update.get('due_date')
                if not due_file or str(due_file).strip().lower() in ['(empty)', 'none', '']:
                    raise ValueError("Due Date cannot be empty (Database constraint). Please provide a valid date.")
                else:
                    update_kwargs['due_date'] = normalize_date_for_django(due_file)

                # Apply cleared date
                cleared_file = update.get('cleared_date')
                if cleared_file and str(cleared_file).strip().lower() not in ['(empty)', 'none', '']:
                    update_kwargs['cleared_date'] = normalize_date_for_django(cleared_file)
                else:
                    update_kwargs['cleared_date'] = None

                # Apply raised date (optional)
                raised_file = update.get('raised_date')
                if raised_file and str(raised_file).strip().lower() not in ['(empty)', 'none', '']:
                    update_kwargs['raised_date'] = normalize_date_for_django(raised_file)
                else:
                    update_kwargs['raised_date'] = None

                # Use .update() instead of .save() to bypass full_clean() validation on corrupted fields
                Deficiency.objects.filter(pk=record.pk).update(**update_kwargs)

                # Sync in-memory record to prevent the script from detecting false differences later
                if 'status' in update_kwargs:
                    record.status = update_kwargs['status']
                if 'due_date' in update_kwargs:
                    record.due_date = update_kwargs['due_date']
                if 'cleared_date' in update_kwargs:
                    record.cleared_date = update_kwargs['cleared_date']
                if 'raised_date' in update_kwargs:
                    record.raised_date = update_kwargs['raised_date']

            self.stdout.write(self.style.SUCCESS('✓ Update applied successfully'))
            logging.info(f"DR#{dr_num}: Update applied successfully.")
            return True

        except Exception as e:
            error_msg = f'✗ Error applying update: {str(e)}'
            self.stderr.write(self.style.ERROR(error_msg))
            logging.error(f"DR#{dr_num}: {error_msg}")
            return False

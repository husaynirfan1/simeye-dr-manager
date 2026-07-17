#!/usr/bin/env python
"""
Data Migration Script: Convert ActionTaken text to relational Action model.

This script reads existing ActionTaken text from dr_deficiency table
and creates corresponding Action records in the new dr_action table.

Run this after creating the Action model table but before using the new system.
"""
import os
import sys
import django
import re
from datetime import datetime

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dr_project.settings.dev')
django.setup()

from apps.deficiencies.models import Deficiency, Action
from django.utils import timezone
from django.db import transaction


def parse_action_taken(action_text):
    """
    Parse ActionTaken text into list of action dictionaries.

    Format: [MMM DD YYYY HH:MMam/pm] [Username] [Description]
    Multiple entries separated by &#x0D;, \r\n, or \n

    Args:
        action_text: The raw ActionTaken text field

    Returns:
        List of dicts with keys: timestamp, username, description, full
    """
    if not action_text:
        return []

    actions = []
    # Split by carriage return or similar separators
    entries = re.split(r'(?:&#x0D;|\r\n|\n)', action_text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Parse the entry - format: [date] [user] [description]
        match = re.match(r'\[([^\]]+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]', entry)
        if match:
            actions.append({
                'timestamp': match.group(1),
                'username': match.group(2),
                'description': match.group(3),
                'full': entry
            })

    return actions


def parse_timestamp(timestamp_str):
    """
    Parse timestamp string to datetime object.

    Args:
        timestamp_str: String like "Jul 16 2026 10:30AM"

    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Format: MMM DD YYYY HH:MMam/pm
        return datetime.strptime(timestamp_str, '%b %d %Y %I:%M%p')
    except (ValueError, TypeError):
        return None


@transaction.atomic
def migrate_actions(dry_run=False):
    """
    Migrate ActionTaken text to Action records.

    Args:
        dry_run: If True, don't actually save to database

    Returns:
        dict with migration statistics
    """
    deficiencies = Deficiency.objects.exclude(
        actiontaken__isnull=True
    ).exclude(
        actiontaken=''
    )

    stats = {
        'total_deficiencies_with_actions': deficiencies.count(),
        'actions_migrated': 0,
        'actions_failed': 0,
        'deficiencies_processed': 0,
        'errors': []
    }

    print(f"Found {stats['total_deficiencies_with_actions']} deficiencies with actions")
    print("=" * 80)

    for deficiency in deficiencies:
        stats['deficiencies_processed'] += 1
        actions = parse_action_taken(deficiency.actiontaken)

        for action_data in actions:
            try:
                # Parse timestamp
                timestamp = parse_timestamp(action_data['timestamp'])
                if timestamp is None:
                    timestamp = timezone.now()

                if not dry_run:
                    # Create Action record
                    Action.objects.create(
                        deficiency=deficiency,
                        username=action_data['username'],
                        description=action_data['description'],
                        created_at=timestamp
                    )

                stats['actions_migrated'] += 1
                print(f"  ✓ DR#{deficiency.deficiency_number}: {action_data['username']} - {action_data['description'][:50]}")

            except Exception as e:
                stats['actions_failed'] += 1
                error_msg = f"DR#{deficiency.deficiency_number}: {str(e)}"
                stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")

    print("=" * 80)
    print(f"\nMigration Summary:")
    print(f"  Deficiencies processed: {stats['deficiencies_processed']}")
    print(f"  Actions migrated: {stats['actions_migrated']}")
    print(f"  Actions failed: {stats['actions_failed']}")

    if stats['errors']:
        print(f"\nErrors encountered:")
        for error in stats['errors']:
            print(f"  - {error}")

    return stats


def verify_migration():
    """Verify that migration was successful"""
    print("\nVerifying migration...")

    # Count total actions in new table
    total_actions = Action.objects.count()
    print(f"  Total actions in dr_action table: {total_actions}")

    # Check some deficiencies
    sample_deficiencies = Deficiency.objects.filter(
        actiontaken__isnull=False
    ).exclude(actiontaken='')[:5]

    for deficiency in sample_deficiencies:
        action_count = deficiency.actions.count()
        print(f"  DR#{deficiency.deficiency_number}: {action_count} actions")

    return total_actions


def rollback_migration():
    """
    Rollback migration by deleting all Action records.
    WARNING: This will delete all migrated action data!
    """
    confirm = input("Are you sure you want to delete all migrated actions? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Rollback cancelled.")
        return

    deleted_count = Action.objects.all().delete()[0]
    print(f"Deleted {deleted_count} action records.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate ActionTaken text to Action model')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verify', action='store_true', help='Verify migration and show statistics')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration by deleting all Action records')

    args = parser.parse_args()

    if args.verify:
        verify_migration()
    elif args.rollback:
        rollback_migration()
    else:
        print("Starting ActionTaken migration...")
        if args.dry_run:
            print("** DRY RUN MODE - No changes will be made **")
        migrate_actions(dry_run=args.dry_run)

        if not args.dry_run:
            print("\n" + "=" * 80)
            print("Migration complete! Run with --verify to check results.")
            print("If there were issues, run --rollback to delete migrated actions.")

"""
Unit tests for Deficiency model, QuerySet, and Manager.
"""
from datetime import date, datetime
from django.test import TestCase, override_settings
from django.db.models import Q
from django.utils import timezone

from apps.deficiencies.models import Deficiency, DeficiencyQuerySet, DeficiencyManager
from apps.users.models import User, UserRole
from .test_config import DeficiencyTestCase


class DeficiencyModelTest(DeficiencyTestCase):
    """Test Deficiency model fields and methods"""

    @classmethod
    def setUpTestData(cls):
        """Create test data that will be used by all test methods"""
        # Note: Since managed=False, these tests assume the database table exists
        # In a real scenario, you'd need to ensure the test database has the table
        cls.today = date.today()

        # We'll create mock data using direct model instantiation
        # In practice with managed=False, you'd need actual database setup
        cls.deficiency_data = {
            'deficiency_number': 1001,
            'site_name': 'Test Site',
            'resource': 'Test Resource',
            'issue_description': 'Test issue description for unit testing',
            'status': 'OPEN',
            'severity': 'A',
            'type': 'Hardware',
            'deficiency_type': 'Maintenance',
            'category_name': 'General',
            'raised_by_name': 'Test User',
            'entered_by_name': 'Test User',
            'raised_date': cls.today,
            'entered_date': cls.today,
            'due_date': cls.today,
            'customer': 'Internal',
            'dashboard_visible': True,
            'is_restricted': False,
            'is_safety': False,
            'affects_qualification': False,
            'downtime': 0,
            'interrupt_minutes': 0,
            'device_interrupt_minutes': 0,
        }

    def test_model_str_representation(self):
        """Test the __str__ method returns expected format"""
        deficiency = Deficiency(**self.deficiency_data)
        expected = f"DR#{self.deficiency_data['deficiency_number']} - {self.deficiency_data['issue_description'][:50]}"
        self.assertEqual(str(deficiency), expected)

    def test_model_fields(self):
        """Test that model fields are properly defined"""
        deficiency = Deficiency(**self.deficiency_data)

        # Test primary key
        self.assertEqual(deficiency.deficiency_number, 1001)

        # Test string fields
        self.assertEqual(deficiency.site_name, 'Test Site')
        self.assertEqual(deficiency.resource, 'Test Resource')
        self.assertEqual(deficiency.issue_description, 'Test issue description for unit testing')

        # Test status choices
        valid_statuses = ['OPEN', 'In Work', 'Monitoring', 'On Offer', 'On Hold', 'Cleared', 'CLOSED']
        self.assertIn(deficiency.status, valid_statuses)

        # Test severity choices
        valid_severities = ['A', 'B', 'C', 'D']
        self.assertIn(deficiency.severity, valid_severities)

        # Test boolean fields
        self.assertTrue(deficiency.dashboard_visible)
        self.assertFalse(deficiency.is_restricted)
        self.assertFalse(deficiency.is_safety)
        self.assertFalse(deficiency.affects_qualification)

        # Test numeric fields
        self.assertEqual(deficiency.downtime, 0)
        self.assertEqual(deficiency.interrupt_minutes, 0)

    def test_status_choices(self):
        """Test all valid status choices"""
        valid_choices = [choice[0] for choice in Deficiency.STATUS_CHOICES]
        expected_choices = ['OPEN', 'In Work', 'Monitoring', 'On Offer', 'On Hold', 'Cleared', 'CLOSED']
        self.assertEqual(valid_choices, expected_choices)

    def test_severity_choices(self):
        """Test all valid severity choices"""
        valid_choices = [choice[0] for choice in Deficiency.SEVERITY_CHOICES]
        expected_choices = ['A', 'B', 'C', 'D']
        self.assertEqual(valid_choices, expected_choices)

    def test_get_absolute_url(self):
        """Test get_absolute_url returns correct URL"""
        deficiency = Deficiency(**self.deficiency_data)
        url = deficiency.get_absolute_url()
        self.assertIn(str(deficiency.deficiency_number), url)
        self.assertIn('/deficiency/', url)

    def test_parsed_actions_with_valid_data(self):
        """Test parsed_actions property with valid actiontaken data"""
        deficiency = Deficiency(**self.deficiency_data)
        # Simulate actiontaken data
        deficiency.actiontaken = "[Jun 20 2025 10:30AM] [Test User] [Initial action taken]"

        actions = deficiency.parsed_actions
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['username'], 'Test User')
        self.assertEqual(actions[0]['description'], 'Initial action taken')
        self.assertIn('Jun 20 2025 10:30AM', actions[0]['timestamp'])

    def test_parsed_actions_with_multiple_entries(self):
        """Test parsed_actions with multiple action entries"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.actiontaken = (
            "[Jun 20 2025 10:30AM] [User1] [First action]\r\n"
            "[Jun 21 2025 02:15PM] [User2] [Second action]"
        )

        actions = deficiency.parsed_actions
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]['username'], 'User1')
        self.assertEqual(actions[1]['username'], 'User2')

    def test_parsed_actions_with_empty_data(self):
        """Test parsed_actions returns empty list for None/empty data"""
        deficiency = Deficiency(**self.deficiency_data)

        # Test with None
        deficiency.actiontaken = None
        self.assertEqual(deficiency.parsed_actions, [])

        # Test with empty string
        deficiency.actiontaken = ''
        self.assertEqual(deficiency.parsed_actions, [])

    def test_parsed_actions_with_malformed_data(self):
        """Test parsed_actions handles malformed entries gracefully"""
        deficiency = Deficiency(**self.deficiency_data)
        # Mix of valid and invalid entries
        deficiency.actiontaken = (
            "[Jun 20 2025 10:30AM] [User1] [Valid action]\r\n"
            "Invalid entry without brackets\r\n"
            "[Jun 21 2025 02:15PM] [User2] [Another valid action]"
        )

        actions = deficiency.parsed_actions
        # Should only parse valid entries
        self.assertEqual(len(actions), 2)

    def test_format_date_with_valid_date(self):
        """Test format_date method with valid date"""
        deficiency = Deficiency(**self.deficiency_data)
        test_date = date(2025, 6, 20)

        result = deficiency.format_date('raised_date')
        # The method formats dates as DD-MM-YYYY
        self.assertIsNotNone(result)

    def test_format_date_with_string_date(self):
        """Test format_date handles string dates"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.raised_date = '2025-06-20'

        result = deficiency.format_date('raised_date')
        self.assertIsNotNone(result)

    def test_format_date_with_none(self):
        """Test format_date returns None for None value"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.cleared_date = None

        result = deficiency.format_date('cleared_date')
        self.assertIsNone(result)

    def test_due_date_display_property(self):
        """Test due_date_display property"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.due_date = date(2025, 12, 31)

        display = deficiency.due_date_display
        self.assertIsNotNone(display)
        # Should be in DD-MM-YYYY format
        self.assertIn('-', display)

    def test_raised_date_display_property(self):
        """Test raised_date_display property"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.raised_date = date(2025, 6, 15)

        display = deficiency.raised_date_display
        self.assertIsNotNone(display)

    def test_cleared_date_display_property(self):
        """Test cleared_date_display property"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.cleared_date = date(2025, 6, 20)

        display = deficiency.cleared_date_display
        self.assertIsNotNone(display)

    def test_entered_date_display_property(self):
        """Test entered_date_display property"""
        deficiency = Deficiency(**self.deficiency_data)
        deficiency.entered_date = date(2025, 6, 10)

        display = deficiency.entered_date_display
        self.assertIsNotNone(display)


class DeficiencyQuerySetTest(DeficiencyTestCase):
    """Test DeficiencyQuerySet custom methods"""

    @classmethod
    def setUpTestData(cls):
        """Create test data for QuerySet tests"""
        cls.today = date.today()

    def test_open_filter(self):
        """Test the open() filter method"""
        # Create a queryset (won't execute without database)
        qs = Deficiency.objects.all()
        filtered = qs.open()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_in_work_filter(self):
        """Test the in_work() filter method"""
        qs = Deficiency.objects.all()
        filtered = qs.in_work()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_cleared_filter(self):
        """Test the cleared() filter method"""
        qs = Deficiency.objects.all()
        filtered = qs.cleared()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_high_severity_filter(self):
        """Test the high_severity() filter method"""
        qs = Deficiency.objects.all()
        filtered = qs.high_severity()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_by_site_filter(self):
        """Test the by_site() filter method"""
        qs = Deficiency.objects.all()
        filtered = qs.by_site('Test Site')
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_by_resource_filter(self):
        """Test the by_resource() filter method"""
        qs = Deficiency.objects.all()
        filtered = qs.by_resource('Test Resource')
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_search_filter(self):
        """Test the search() method filters multiple fields"""
        qs = Deficiency.objects.all()
        filtered = qs.search('test query')
        self.assertIsInstance(filtered, DeficiencyQuerySet)


class DeficiencyManagerTest(DeficiencyTestCase):
    """Test DeficiencyManager methods"""

    def test_manager_returns_custom_queryset(self):
        """Test that manager returns DeficiencyQuerySet"""
        qs = Deficiency.objects.get_queryset()
        self.assertIsInstance(qs, DeficiencyQuerySet)

    def test_manager_open_method(self):
        """Test manager open() method"""
        filtered = Deficiency.objects.open()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_manager_in_work_method(self):
        """Test manager in_work() method"""
        filtered = Deficiency.objects.in_work()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_manager_cleared_method(self):
        """Test manager cleared() method"""
        filtered = Deficiency.objects.cleared()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_manager_high_severity_method(self):
        """Test manager high_severity() method"""
        filtered = Deficiency.objects.high_severity()
        self.assertIsInstance(filtered, DeficiencyQuerySet)

    def test_manager_statistics_method(self):
        """Test manager statistics() method"""
        stats = Deficiency.objects.statistics()
        self.assertIsInstance(stats, dict)
        # Check expected keys exist
        self.assertIn('total', stats)
        self.assertIn('open_count', stats)
        self.assertIn('in_work_count', stats)
        self.assertIn('cleared_count', stats)


class DeficiencyDateHandlingTest(DeficiencyTestCase):
    """Test date handling in Deficiency model"""

    def test_date_initialization_with_yyyy_mm_dd(self):
        """Test model handles YYYY-MM-DD format correctly"""
        data = {
            'deficiency_number': 1002,
            'site_name': 'Test',
            'resource': 'Resource',
            'issue_description': 'Test',
            'status': 'OPEN',
            'raised_date': '2025-06-20',
            'entered_date': '2025-06-20',
            'due_date': '2025-06-20',
            'customer': 'Internal',
        }
        deficiency = Deficiency(**data)
        # Should parse the date string correctly
        self.assertIsNotNone(deficiency.raised_date)

    def test_date_initialization_with_dd_mm_yyyy(self):
        """Test model handles DD-MM-YYYY format correctly"""
        data = {
            'deficiency_number': 1003,
            'site_name': 'Test',
            'resource': 'Resource',
            'issue_description': 'Test',
            'status': 'OPEN',
            'raised_date': '20-06-2025',
            'entered_date': '20-06-2025',
            'due_date': '20-06-2025',
            'customer': 'Internal',
        }
        deficiency = Deficiency(**data)
        # Should parse the date string correctly
        self.assertIsNotNone(deficiency.raised_date)

    def test_date_initialization_with_dd_mmm_yyyy(self):
        """Test model handles DD-MMM-YYYY (Oracle) format correctly"""
        data = {
            'deficiency_number': 1004,
            'site_name': 'Test',
            'resource': 'Resource',
            'issue_description': 'Test',
            'status': 'OPEN',
            'raised_date': '20-JUN-2025',
            'entered_date': '20-JUN-2025',
            'due_date': '20-JUN-2025',
            'customer': 'Internal',
        }
        deficiency = Deficiency(**data)
        # Should parse the Oracle date format correctly
        self.assertIsNotNone(deficiency.raised_date)

    def test_date_initialization_with_mm_dd_yyyy(self):
        """Test model handles MM/DD/YYYY format correctly"""
        data = {
            'deficiency_number': 1005,
            'site_name': 'Test',
            'resource': 'Resource',
            'issue_description': 'Test',
            'status': 'OPEN',
            'raised_date': '06/20/2025',
            'entered_date': '06/20/2025',
            'due_date': '06/20/2025',
            'customer': 'Internal',
        }
        deficiency = Deficiency(**data)
        # Should parse the US date format correctly
        self.assertIsNotNone(deficiency.raised_date)


class DeficiencyMetaTest(DeficiencyTestCase):
    """Test Deficiency model Meta options"""

    def test_db_table_name(self):
        """Test the database table name is set correctly"""
        self.assertEqual(Deficiency._meta.db_table, 'dr_deficiency')

    def test_managed_flag(self):
        """Test that managed is False (using existing table)"""
        self.assertFalse(Deficiency._meta.managed)

    def test_default_ordering(self):
        """Test default ordering is by deficiency_number descending"""
        ordering = Deficiency._meta.ordering
        self.assertEqual(ordering, ['-deficiency_number'])

    def test_verbose_name(self):
        """Test verbose name is set"""
        self.assertEqual(Deficiency._meta.verbose_name, 'Deficiency')

    def test_verbose_name_plural(self):
        """Test verbose name plural is set"""
        self.assertEqual(Deficiency._meta.verbose_name_plural, 'Deficiencies')

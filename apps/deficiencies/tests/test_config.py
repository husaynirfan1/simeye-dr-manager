"""
Test configuration and fixtures for deficiencies app tests.
Handles managed=False models during testing.
"""
from django.test import TestCase
from django.db import connection
from apps.deficiencies.models import Deficiency
from apps.users.models import User, UserRole


def create_deficiency_table_if_not_exists():
    """Create the dr_deficiency table in the test database if it doesn't exist."""
    table_name = 'dr_deficiency'
    vendor = connection.vendor

    with connection.cursor() as cursor:
        # Check if table exists based on database vendor
        if vendor == 'sqlite':
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name=%s
            """, [table_name])
        elif vendor == 'postgresql':
            cursor.execute("""
                SELECT tablename FROM pg_tables WHERE tablename=%s
            """, [table_name])
        else:
            # Fallback - try to query and catch the error
            try:
                cursor.execute(f'SELECT 1 FROM "{table_name}" LIMIT 1')
            except:
                pass  # Table doesn't exist, will create below
                return

        if not cursor.fetchone():
            # Create the table with the schema from the model
            # Use different syntax based on database vendor
            if vendor == 'postgresql':
                cursor.execute(f"""
                    CREATE TABLE "{table_name}" (
                        "DeficiencyNumber" INTEGER PRIMARY KEY,
                        "SiteName" VARCHAR(100),
                        "Resource" VARCHAR(100),
                        "Issue_Description" TEXT,
                        "Status" VARCHAR(20) DEFAULT 'OPEN',
                        "Severity" VARCHAR(1) DEFAULT 'C',
                        "SubStatusName" VARCHAR(100),
                        "Type" VARCHAR(50) DEFAULT 'Hardware',
                        "DeficiencyType" VARCHAR(50) DEFAULT 'Maintenance',
                        "CategoryName" VARCHAR(100) DEFAULT 'General',
                        "RaisedByName" VARCHAR(255) DEFAULT 'System',
                        "AssigneeName" VARCHAR(255),
                        "AssigneeGroupName" VARCHAR(255),
                        "EnteredByName" VARCHAR(255) DEFAULT 'System',
                        "ClearedbyName" VARCHAR(255),
                        "RaisedDate" DATE,
                        "EnteredDate" DATE,
                        "ClearedDate" DATE,
                        "DueDate" DATE NOT NULL DEFAULT CURRENT_DATE,
                        "NAADueDate" DATE,
                        "OnOfferDate" DATE,
                        "_RaisedDate" TIMESTAMP,
                        "_EnteredDate" TIMESTAMP,
                        "_ClearedDate" TIMESTAMP,
                        "_DueDate" TIMESTAMP,
                        "fldRaisedDate" DATE,
                        "fldDueDate" DATE,
                        "fldLastActionTakenDate" DATE,
                        "DownTime" INTEGER DEFAULT 0,
                        "InterruptMinutes" INTEGER DEFAULT 0,
                        "DeviceInterruptMinutes" INTEGER DEFAULT 0,
                        "Is_Restricted" BOOLEAN DEFAULT FALSE,
                        "Is_Safety" BOOLEAN DEFAULT FALSE,
                        "Affects_Qualification" BOOLEAN DEFAULT FALSE,
                        "DashboardVisible" BOOLEAN DEFAULT TRUE,
                        "SPR" VARCHAR(50),
                        "TrackingNumber" VARCHAR(50),
                        "System" VARCHAR(100),
                        "SubSystem" VARCHAR(100),
                        "Conversion" TEXT,
                        "Configuration" TEXT,
                        "Restriction" TEXT,
                        "AlternateMethod" TEXT,
                        "Customer" VARCHAR(255) DEFAULT 'Internal',
                        "fldResourceId" INTEGER DEFAULT 1,
                        "fldRaisedById" INTEGER DEFAULT 1,
                        "fldEnteredById" INTEGER DEFAULT 1,
                        "ActionTaken" TEXT
                    )
                """)
            else:  # SQLite
                cursor.execute(f"""
                    CREATE TABLE "{table_name}" (
                        "DeficiencyNumber" INTEGER PRIMARY KEY,
                        "SiteName" VARCHAR(100),
                        "Resource" VARCHAR(100),
                        "Issue_Description" TEXT,
                        "Status" VARCHAR(20) DEFAULT 'OPEN',
                        "Severity" VARCHAR(1) DEFAULT 'C',
                        "SubStatusName" VARCHAR(100),
                        "Type" VARCHAR(50) DEFAULT 'Hardware',
                        "DeficiencyType" VARCHAR(50) DEFAULT 'Maintenance',
                        "CategoryName" VARCHAR(100) DEFAULT 'General',
                        "RaisedByName" VARCHAR(255) DEFAULT 'System',
                        "AssigneeName" VARCHAR(255),
                        "AssigneeGroupName" VARCHAR(255),
                        "EnteredByName" VARCHAR(255) DEFAULT 'System',
                        "ClearedbyName" VARCHAR(255),
                        "RaisedDate" DATE,
                        "EnteredDate" DATE,
                        "ClearedDate" DATE,
                        "DueDate" DATE NOT NULL DEFAULT (date('now')),
                        "NAADueDate" DATE,
                        "OnOfferDate" DATE,
                        "_RaisedDate" TIMESTAMP,
                        "_EnteredDate" TIMESTAMP,
                        "_ClearedDate" TIMESTAMP,
                        "_DueDate" TIMESTAMP,
                        "fldRaisedDate" DATE,
                        "fldDueDate" DATE,
                        "fldLastActionTakenDate" DATE,
                        "DownTime" INTEGER DEFAULT 0,
                        "InterruptMinutes" INTEGER DEFAULT 0,
                        "DeviceInterruptMinutes" INTEGER DEFAULT 0,
                        "Is_Restricted" BOOLEAN DEFAULT 0,
                        "Is_Safety" BOOLEAN DEFAULT 0,
                        "Affects_Qualification" BOOLEAN DEFAULT 0,
                        "DashboardVisible" BOOLEAN DEFAULT 1,
                        "SPR" VARCHAR(50),
                        "TrackingNumber" VARCHAR(50),
                        "System" VARCHAR(100),
                        "SubSystem" VARCHAR(100),
                        "Conversion" TEXT,
                        "Configuration" TEXT,
                        "Restriction" TEXT,
                        "AlternateMethod" TEXT,
                        "Customer" VARCHAR(255) DEFAULT 'Internal',
                        "fldResourceId" INTEGER DEFAULT 1,
                        "fldRaisedById" INTEGER DEFAULT 1,
                        "fldEnteredById" INTEGER DEFAULT 1,
                        "ActionTaken" TEXT
                    )
                """)


class DeficiencyTestCase(TestCase):
    """
    Base test case that handles the managed=False Deficiency model.
    Ensures the database table exists before tests run.
    """

    @classmethod
    def setUpClass(cls):
        """Ensure the deficiency table exists before tests run"""
        # Temporarily set managed=True
        original_managed = Deficiency._meta.managed
        Deficiency._meta.managed = True

        # Create the table if it doesn't exist
        create_deficiency_table_if_not_exists()

        super().setUpClass()

        # Restore original managed setting
        Deficiency._meta.managed = original_managed

    def setUp(self):
        """Set up test data"""
        super().setUp()

    def tearDown(self):
        """Clean up after each test"""
        super().tearDown()

    @classmethod
    def create_test_users(cls):
        """Helper to create test users"""
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=UserRole.ADMIN,
            first_name='Admin',
            last_name='User'
        )

        cls.technician_user = User.objects.create_user(
            username='tech',
            email='tech@test.com',
            password='testpass123',
            role=UserRole.TECHNICIAN,
            first_name='Tech',
            last_name='User'
        )

        cls.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@test.com',
            password='testpass123',
            role=UserRole.VIEWER,
            first_name='Viewer',
            last_name='User'
        )


def create_test_deficiency(**kwargs):
    """
    Helper function to create a test Deficiency record.
    All fields have sensible defaults for testing.
    """
    from datetime import date

    defaults = {
        'deficiency_number': kwargs.get('deficiency_number', 1000),
        'site_name': kwargs.get('site_name', 'Test Site'),
        'resource': kwargs.get('resource', 'Test Resource'),
        'issue_description': kwargs.get('issue_description', 'Test issue for unit testing'),
        'status': kwargs.get('status', 'OPEN'),
        'severity': kwargs.get('severity', 'C'),
        'type': kwargs.get('type', 'Hardware'),
        'deficiency_type': kwargs.get('deficiency_type', 'Maintenance'),
        'category_name': kwargs.get('category_name', 'General'),
        'raised_by_name': kwargs.get('raised_by_name', 'Test User'),
        'entered_by_name': kwargs.get('entered_by_name', 'Test User'),
        'raised_date': kwargs.get('raised_date', date.today()),
        'entered_date': kwargs.get('entered_date', date.today()),
        'due_date': kwargs.get('due_date', date.today()),
        'customer': kwargs.get('customer', 'Internal'),
        'dashboard_visible': kwargs.get('dashboard_visible', True),
        'is_restricted': kwargs.get('is_restricted', False),
        'is_safety': kwargs.get('is_safety', False),
        'affects_qualification': kwargs.get('affects_qualification', False),
        'downtime': kwargs.get('downtime', 0),
        'interrupt_minutes': kwargs.get('interrupt_minutes', 0),
        'device_interrupt_minutes': kwargs.get('device_interrupt_minutes', 0),
        'fld_resource_id': kwargs.get('fld_resource_id', 1),
        'fld_raised_by_id': kwargs.get('fld_raised_by_id', 1),
        'fld_entered_by_id': kwargs.get('fld_entered_by_id', 1),
    }
    # Update with any provided kwargs (only for keys not in defaults)
    defaults.update({k: v for k, v in kwargs.items() if k not in defaults})

    return Deficiency.objects.create(**defaults)

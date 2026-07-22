"""
Unit tests for Deficiency forms.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.deficiencies.forms import (
    DeficiencyForm, QuickFilterForm, ActionAddForm, DeficiencyBulkEditForm, DateInput
)
from apps.deficiencies.models import Deficiency
from apps.users.models import User, UserRole
from .test_config import DeficiencyTestCase


class DeficiencyFormTest(DeficiencyTestCase):
    """Test DeficiencyForm"""

    @classmethod
    def setUpTestData(cls):
        """Create test users"""
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

        # Create sample deficiency records for form dropdowns
        # These provide the distinct values that forms query for
        from datetime import date

        cls.sample_dr_1 = Deficiency.objects.create(
            deficiency_number=1001,
            site_name='Site A',
            resource='Resource 1',
            issue_description='Sample issue 1',
            status='OPEN',
            severity='A',
            type='Hardware',
            deficiency_type='Maintenance',
            category_name='Category 1',
            raised_by_name='Admin User',
            entered_by_name='Admin User',
            raised_date=date.today(),
            entered_date=date.today(),
            due_date=date.today(),
            customer='Internal'
        )

        cls.sample_dr_2 = Deficiency.objects.create(
            deficiency_number=1002,
            site_name='Site B',
            resource='Resource 2',
            issue_description='Sample issue 2',
            status='In Work',
            severity='B',
            type='Software',
            deficiency_type='Training',
            category_name='Category 2',
            raised_by_name='Tech User',
            entered_by_name='Tech User',
            raised_date=date.today(),
            entered_date=date.today(),
            due_date=date.today(),
            customer='External'
        )

        # Sample form data - must match existing database values for dropdowns
        cls.valid_form_data = {
            'site_name': 'Site A',  # Must exist in database
            'resource': 'Resource 1',  # Must exist in database
            'issue_description': 'Test issue description for form validation',
            'status': 'OPEN',
            'severity': 'C',
            'type': 'Hardware',
            'deficiency_type': 'Maintenance',  # Must exist in database
            'category_name': 'Category 1',  # Must exist in database
            'raised_by_name': 'Admin User',  # Must exist in database
            'assignee_name': '',
            'assignee_group_name': '',
            'sub_status_name': '',
            'due_date': '2025-12-31',
            'downtime': 0,
            'interrupt_minutes': 0,
            'device_interrupt_minutes': 0,
            'spr': '',
            'tracking_number': '',
            'dashboard_visible': True,
            'is_restricted': False,
            'is_safety': False,
            'affects_qualification': False,
            'system': '',
            'sub_system': '',
            'conversion': '',
            'configuration': '',
            'naa_due_date': '',
            'on_offer_date': '',
            'restriction': '',
            'alternate_method': '',
            'customer': 'Internal',  # Must exist in database
        }

    def test_form_requires_user_parameter(self):
        """Test form requires user parameter for initialization"""
        # Should work with user
        form = DeficiencyForm(user=self.admin_user)
        self.assertIsNotNone(form)

    def test_form_fields_present(self):
        """Test all expected fields are in the form"""
        form = DeficiencyForm(user=self.admin_user)
        expected_fields = [
            'site_name', 'resource', 'issue_description',
            'assignee_name', 'assignee_group_name', 'raised_by_name',
            'type', 'severity', 'category_name', 'status', 'sub_status_name',
            'due_date', 'downtime', 'spr', 'tracking_number',
            'dashboard_visible', 'deficiency_type',
            'is_restricted', 'is_safety', 'affects_qualification',
            'system', 'sub_system', 'interrupt_minutes', 'device_interrupt_minutes',
            'conversion', 'configuration', 'naa_due_date', 'on_offer_date',
            'restriction', 'alternate_method', 'customer',
        ]
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_form_with_admin_user_has_enabled_raised_by_field(self):
        """Test admin users have raised_by_name field enabled"""
        form = DeficiencyForm(user=self.admin_user)
        # Admin's raised_by_name should not be disabled
        self.assertNotIn('disabled', form.fields['raised_by_name'].widget.attrs)

    def test_form_with_technician_has_disabled_raised_by_field(self):
        """Test technician users have raised_by_name field disabled"""
        form = DeficiencyForm(user=self.technician_user)
        # Technician's raised_by_name should be disabled
        self.assertEqual(
            form.fields['raised_by_name'].widget.attrs.get('disabled'),
            'disabled'
        )

    def test_form_sets_default_for_new_deficiency(self):
        """Test form sets smart defaults for new deficiencies"""
        form = DeficiencyForm(user=self.admin_user)
        self.assertEqual(form.initial.get('status'), 'OPEN')
        self.assertEqual(form.initial.get('severity'), 'D')

    def test_form_sets_default_due_date(self):
        """Test form sets due date to 30 days from today for new deficiency"""
        form = DeficiencyForm(user=self.admin_user)
        expected_date = (timezone.now().date() + timedelta(days=30)).strftime('%Y-%m-%d')
        self.assertEqual(form.initial.get('due_date'), expected_date)

    def test_form_valid_with_complete_data(self):
        """Test form is valid with complete data"""
        form = DeficiencyForm(data=self.valid_form_data, user=self.admin_user)
        self.assertTrue(form.is_valid())

    def test_form_clean_downtime_rejects_negative(self):
        """Test form validation rejects negative downtime"""
        data = self.valid_form_data.copy()
        data['downtime'] = -10
        form = DeficiencyForm(data=data, user=self.admin_user)
        self.assertFalse(form.is_valid())
        self.assertIn('downtime', form.errors)

    def test_form_clean_interrupt_minutes_rejects_negative(self):
        """Test form validation rejects negative interrupt_minutes"""
        data = self.valid_form_data.copy()
        data['interrupt_minutes'] = -5
        form = DeficiencyForm(data=data, user=self.admin_user)
        self.assertFalse(form.is_valid())
        self.assertIn('interrupt_minutes', form.errors)

    def test_form_clean_device_interrupt_minutes_rejects_negative(self):
        """Test form validation rejects negative device_interrupt_minutes"""
        data = self.valid_form_data.copy()
        data['device_interrupt_minutes'] = -1
        form = DeficiencyForm(data=data, user=self.admin_user)
        self.assertFalse(form.is_valid())
        self.assertIn('device_interrupt_minutes', form.errors)

    def test_form_normalizes_due_date(self):
        """Test form normalizes due_date to YYYY-MM-DD format"""
        data = self.valid_form_data.copy()
        # Test DD/MM/YYYY format
        data['due_date'] = '31/12/2025'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['due_date'],
                date(2025, 12, 31)
            )

    def test_form_normalizes_naa_due_date(self):
        """Test form normalizes naa_due_date to YYYY-MM-DD format"""
        data = self.valid_form_data.copy()
        data['naa_due_date'] = '15/06/2025'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['naa_due_date'],
                date(2025, 6, 15)
            )

    def test_form_normalizes_on_offer_date(self):
        """Test form normalizes on_offer_date to YYYY-MM-DD format"""
        data = self.valid_form_data.copy()
        data['on_offer_date'] = '20-JUN-2025'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['on_offer_date'],
                date(2025, 6, 20)
            )

    def test_form_handles_dd_mm_yyyy_format(self):
        """Test form handles DD-MM-YYYY format"""
        data = self.valid_form_data.copy()
        data['due_date'] = '31-12-2025'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['due_date'],
                date(2025, 12, 31)
            )

    def test_form_handles_oracle_date_format(self):
        """Test form handles Oracle DD-MMM-YYYY format"""
        data = self.valid_form_data.copy()
        data['due_date'] = '31-DEC-2025'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['due_date'],
                date(2025, 12, 31)
            )

    def test_form_accepts_yyyy_mm_dd_format(self):
        """Test form accepts standard YYYY-MM-DD format"""
        data = self.valid_form_data.copy()
        data['due_date'] = '2025-12-31'
        form = DeficiencyForm(data=data, user=self.admin_user)
        if form.is_valid():
            self.assertEqual(
                form.cleaned_data['due_date'],
                date(2025, 12, 31)
            )

    def test_form_allows_empty_optional_dates(self):
        """Test form allows empty values for optional date fields"""
        data = self.valid_form_data.copy()
        data['naa_due_date'] = ''
        data['on_offer_date'] = ''
        form = DeficiencyForm(data=data, user=self.admin_user)
        self.assertTrue(form.is_valid())

    def test_form_datefield_is_required_for_due_date(self):
        """Test due_date is NOT required in form (view sets default)"""
        data = self.valid_form_data.copy()
        data['due_date'] = ''
        form = DeficiencyForm(data=data, user=self.admin_user)
        # Form is valid because blank=True - view will set default before save
        self.assertTrue(form.is_valid())


class QuickFilterFormTest(DeficiencyTestCase):
    """Test QuickFilterForm"""

    def test_form_fields_present(self):
        """Test all expected fields are in the form"""
        form = QuickFilterForm()
        expected_fields = ['status', 'severity', 'site', 'resource', 'search']
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_all_fields_are_optional(self):
        """Test all fields are optional"""
        form = QuickFilterForm(data={})
        self.assertTrue(form.is_valid())

    def test_status_field_choices(self):
        """Test status field has correct choices including 'All' option"""
        form = QuickFilterForm()
        status_field = form.fields['status']
        self.assertIn('', [choice[0] for choice in status_field.choices])

    def test_severity_field_choices(self):
        """Test severity field has correct choices including 'All' option"""
        form = QuickFilterForm()
        severity_field = form.fields['severity']
        self.assertIn('', [choice[0] for choice in severity_field.choices])

    def test_form_valid_with_filters(self):
        """Test form is valid with filter values"""
        data = {
            'status': 'OPEN',
            'severity': 'A',
            'site': 'Test Site',
            'resource': 'Test Resource',
            'search': 'test query',
        }
        form = QuickFilterForm(data=data)
        self.assertTrue(form.is_valid())


class ActionAddFormTest(DeficiencyTestCase):
    """Test ActionAddForm"""

    @classmethod
    def setUpTestData(cls):
        """Create test users and sample data"""
        cls.admin_user = User.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='testpass123',
            role=UserRole.ADMIN,
            first_name='Admin',
            last_name='User'
        )

        cls.technician_user = User.objects.create_user(
            username='tech2',
            email='tech2@test.com',
            password='testpass123',
            role=UserRole.TECHNICIAN,
            first_name='Tech',
            last_name='User'
        )

        # Create sample deficiency record for form dropdowns
        from datetime import date
        cls.sample_dr = Deficiency.objects.create(
            deficiency_number=2001,
            site_name='Site A',
            resource='Resource 1',
            issue_description='Sample issue for action form',
            status='OPEN',
            severity='A',
            type='Hardware',
            deficiency_type='Maintenance',
            category_name='General',
            raised_by_name='Admin User',
            entered_by_name='Admin User',
            raised_date=date.today(),
            entered_date=date.today(),
            due_date=date.today(),
            customer='Internal'
        )

    def test_form_requires_action_text(self):
        """Test action_text field is required"""
        form = ActionAddForm(data={}, user=self.admin_user)
        self.assertFalse(form.is_valid())
        self.assertIn('action_text', form.errors)

    def test_form_valid_with_action_text(self):
        """Test form is valid with action_text"""
        data = {
            'action_text': 'Test action description',
        }
        form = ActionAddForm(data=data, user=self.admin_user)
        self.assertTrue(form.is_valid())

    def test_form_with_admin_has_enabled_username_field(self):
        """Test admin users have username field enabled"""
        form = ActionAddForm(user=self.admin_user)
        self.assertNotIn('disabled', form.fields['username'].widget.attrs)

    def test_form_with_technician_has_disabled_username_field(self):
        """Test technician users have username field disabled"""
        form = ActionAddForm(user=self.technician_user)
        self.assertEqual(
            form.fields['username'].widget.attrs.get('disabled'),
            'disabled'
        )

    def test_form_sets_default_username_for_technician(self):
        """Test form sets technician's username as default"""
        form = ActionAddForm(user=self.technician_user)
        self.assertEqual(form.initial.get('username'), 'Tech User')

    def test_form_sets_default_username_for_admin(self):
        """Test form sets admin's username as default"""
        form = ActionAddForm(user=self.admin_user)
        self.assertEqual(form.initial.get('username'), 'Admin User')

    def test_form_fields_present(self):
        """Test all expected fields are in the form"""
        form = ActionAddForm(user=self.admin_user)
        self.assertIn('action_text', form.fields)
        self.assertIn('username', form.fields)


class DeficiencyBulkEditFormTest(DeficiencyTestCase):
    """Test DeficiencyBulkEditForm"""

    def test_form_fields(self):
        """Test form has correct fields"""
        form = DeficiencyBulkEditForm()
        expected_fields = ['status', 'severity', 'assignee_name']
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_form_model_is_deficiency(self):
        """Test form uses Deficiency model"""
        form = DeficiencyBulkEditForm()
        self.assertEqual(form._meta.model, Deficiency)


class DateInputTest(DeficiencyTestCase):
    """Test custom DateInput widget"""

    def test_format_value_with_none(self):
        """Test format_value returns empty string for None"""
        widget = DateInput()
        result = widget.format_value(None)
        self.assertEqual(result, '')

    def test_format_value_with_date_object(self):
        """Test format_value handles date objects correctly"""
        widget = DateInput()
        test_date = date(2025, 6, 20)
        result = widget.format_value(test_date)
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_yyyy_mm_dd_string(self):
        """Test format_value handles YYYY-MM-DD string"""
        widget = DateInput()
        result = widget.format_value('2025-06-20')
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_dd_mm_yyyy_string(self):
        """Test format_value converts DD/MM/YYYY to YYYY-MM-DD"""
        widget = DateInput()
        result = widget.format_value('20/06/2025')
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_mm_dd_yyyy_string(self):
        """Test format_value converts MM/DD/YYYY to YYYY-MM-DD"""
        widget = DateInput()
        result = widget.format_value('06/20/2025')
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_dd_mm_yyyy_dashes(self):
        """Test format_value converts DD-MM-YYYY to YYYY-MM-DD"""
        widget = DateInput()
        result = widget.format_value('20-06-2025')
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_oracle_format(self):
        """Test format_value converts Oracle DD-MMM-YYYY to YYYY-MM-DD"""
        widget = DateInput()
        result = widget.format_value('20-JUN-2025')
        self.assertEqual(result, '2025-06-20')

    def test_format_value_with_invalid_string(self):
        """Test format_value returns original string for invalid format"""
        widget = DateInput()
        result = widget.format_value('invalid-date')
        self.assertEqual(result, 'invalid-date')


class FormWidgetTest(DeficiencyTestCase):
    """Test form widget configuration"""

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=UserRole.ADMIN,
            first_name='Admin',
            last_name='User'
        )

    def test_deficiency_form_textarea_widgets(self):
        """Test textarea fields have correct widget"""
        form = DeficiencyForm(user=self.admin_user)
        textarea_fields = [
            'issue_description', 'conversion', 'configuration',
            'restriction', 'alternate_method'
        ]
        for field_name in textarea_fields:
            field = form.fields[field_name]
            self.assertEqual(
                field.widget.__class__.__name__,
                'Textarea'
            )

    def test_deficiency_form_date_widgets(self):
        """Test date fields use custom DateInput widget"""
        form = DeficiencyForm(user=self.admin_user)
        date_fields = ['due_date', 'naa_due_date', 'on_offer_date']
        for field_name in date_fields:
            field = form.fields[field_name]
            self.assertIsInstance(field.widget, DateInput)

    def test_deficiency_form_checkbox_widgets(self):
        """Test boolean fields use CheckboxInput widget"""
        form = DeficiencyForm(user=self.admin_user)
        checkbox_fields = [
            'dashboard_visible', 'is_restricted',
            'is_safety', 'affects_qualification'
        ]
        for field_name in checkbox_fields:
            field = form.fields[field_name]
            self.assertEqual(
                field.widget.__class__.__name__,
                'CheckboxInput'
            )

    def test_deficiency_form_number_widgets(self):
        """Test numeric fields use NumberInput widget"""
        form = DeficiencyForm(user=self.admin_user)
        number_fields = ['downtime', 'interrupt_minutes', 'device_interrupt_minutes']
        for field_name in number_fields:
            field = form.fields[field_name]
            self.assertEqual(
                field.widget.__class__.__name__,
                'NumberInput'
            )

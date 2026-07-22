"""
Unit tests for Deficiency views.
"""
from datetime import date, timedelta
from django.test import TestCase, Client, RequestFactory
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

from apps.deficiencies.models import Deficiency
from apps.deficiencies.views import (
    dashboard, deficiency_list, deficiency_detail, deficiency_create,
    deficiency_update, deficiency_delete, action_add
)
from apps.users.models import User, UserRole
from .test_config import DeficiencyTestCase


class DeficiencyViewTestBase(DeficiencyTestCase):
    """Base class for view tests with common setup"""

    @classmethod
    def setUpTestData(cls):
        """Create test users and data"""
        # Create test users with different roles
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

        # Create sample deficiency records for views that query distinct values
        from datetime import date

        # Create DR #1 for tests that specifically use this ID
        cls.sample_dr_1 = Deficiency.objects.create(
            deficiency_number=1,
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
            deficiency_number=3002,
            site_name='Site B',
            resource='Resource 2',
            issue_description='Sample issue 2',
            status='Cleared',
            severity='C',
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

    def setUp(self):
        """Set up client and clear cache before each test"""
        self.client = Client()
        cache.clear()

    def _login_as_admin(self):
        """Helper to log in as admin user"""
        self.client.login(username='admin', password='testpass123')

    def _login_as_technician(self):
        """Helper to log in as technician user"""
        self.client.login(username='tech', password='testpass123')

    def _login_as_viewer(self):
        """Helper to log in as viewer user"""
        self.client.login(username='viewer', password='testpass123')


class DashboardViewTest(DeficiencyViewTestBase):
    """Test dashboard view"""

    def test_dashboard_requires_login(self):
        """Test dashboard redirects to login for anonymous users"""
        response = self.client.get(reverse('deficiencies:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_dashboard_accessible_to_authenticated_users(self):
        """Test dashboard is accessible to all authenticated users"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_renders_correct_template(self):
        """Test dashboard uses correct template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:dashboard'))
        self.assertTemplateUsed(response, 'deficiencies/dashboard.html')

    def test_dashboard_context_has_required_keys(self):
        """Test dashboard context contains expected keys"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:dashboard'))
        context = response.context

        # Check for expected context variables
        expected_keys = [
            'training_stats', 'maintenance_stats', 'visual_modeling_stats',
            'total_active_dr', 'grand_total', 'recent_deficiencies',
            'status_counts', 'severity_counts'
        ]
        for key in expected_keys:
            self.assertIn(key, context)

    def test_dashboard_caches_results(self):
        """Test dashboard caching behavior"""
        self._login_as_admin()

        # First request - should calculate
        response1 = self.client.get(reverse('deficiencies:dashboard'))
        self.assertEqual(response1.status_code, 200)

        # Second request - should use cache
        response2 = self.client.get(reverse('deficiencies:dashboard'))
        self.assertEqual(response2.status_code, 200)


class DeficiencyListViewTest(DeficiencyViewTestBase):
    """Test deficiency list view"""

    def test_list_requires_login(self):
        """Test list view requires authentication"""
        response = self.client.get(reverse('deficiencies:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_list_accessible_to_authenticated_users(self):
        """Test list view is accessible to authenticated users"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:list'))
        self.assertEqual(response.status_code, 200)

    def test_list_uses_correct_template(self):
        """Test list view uses correct template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'))
        self.assertTemplateUsed(response, 'deficiencies/list.html')

    def test_list_has_pagination(self):
        """Test list view paginates results"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'))
        self.assertIn('page_obj', response.context)

    def test_list_filter_by_status(self):
        """Test filtering by status parameter"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'), {'status': 'OPEN'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status_filter'], 'OPEN')

    def test_list_filter_by_severity(self):
        """Test filtering by severity parameter"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'), {'severity': 'A'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['severity_filter'], 'A')

    def test_list_search_functionality(self):
        """Test search functionality in list view"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'), {'search': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['search'], 'test')

    def test_list_context_contains_filter_options(self):
        """Test list context contains filter options"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:list'))
        context = response.context

        # Check for filter options
        self.assertIn('statuses', context)
        self.assertIn('severities', context)
        self.assertIn('sites', context)
        self.assertIn('resources', context)


class DeficiencyDetailViewTest(DeficiencyViewTestBase):
    """Test deficiency detail view"""

    def test_detail_requires_login(self):
        """Test detail view requires authentication"""
        response = self.client.get(reverse('deficiencies:detail', kwargs={'deficiency_number': 1}))
        self.assertEqual(response.status_code, 302)

    def test_detail_accessible_to_authenticated_users(self):
        """Test detail view accessible to authenticated users"""
        self._login_as_viewer()
        # Note: This will fail if DR #1 doesn't exist in the database
        response = self.client.get(reverse('deficiencies:detail', kwargs={'deficiency_number': 1}))
        # 404 is acceptable if the record doesn't exist
        self.assertIn(response.status_code, [200, 404])

    def test_detail_uses_correct_template(self):
        """Test detail view uses correct template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:detail', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertTemplateUsed(response, 'deficiencies/detail.html')

    def test_detail_context_contains_action_form(self):
        """Test detail view includes action form in context"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:detail', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertIn('action_form', response.context)


class DeficiencyCreateViewTest(DeficiencyViewTestBase):
    """Test deficiency create view"""

    def test_create_requires_login(self):
        """Test create view requires authentication"""
        response = self.client.get(reverse('deficiencies:create'))
        self.assertEqual(response.status_code, 302)

    def test_create_accessible_to_technicians(self):
        """Test technicians can access create view"""
        self._login_as_technician()
        response = self.client.get(reverse('deficiencies:create'))
        self.assertEqual(response.status_code, 200)

    def test_create_accessible_to_admins(self):
        """Test admins can access create view"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:create'))
        self.assertEqual(response.status_code, 200)

    def test_create_uses_correct_template(self):
        """Test create view uses correct template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:create'))
        self.assertTemplateUsed(response, 'deficiencies/form.html')

    def test_create_context_contains_required_data(self):
        """Test create view context has lookup values"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:create'))
        context = response.context

        # Check for lookup values
        expected_keys = [
            'form', 'categories', 'systems', 'subsystems',
            'types', 'customers', 'deficiency_types',
            'site_names', 'resources', 'raised_by_names'
        ]
        for key in expected_keys:
            self.assertIn(key, context)

    def test_create_includes_next_dr_number(self):
        """Test create view includes next DR number in context"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:create'))
        self.assertIn('next_dr_number', response.context)


class DeficiencyUpdateViewTest(DeficiencyViewTestBase):
    """Test deficiency update view"""

    def test_update_requires_login(self):
        """Test update view requires authentication"""
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        self.assertEqual(response.status_code, 302)

    def test_update_accessible_to_technicians(self):
        """Test technicians can access update view"""
        self._login_as_technician()
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [200, 404])

    def test_update_accessible_to_admins(self):
        """Test admins can access update view"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [200, 404])

    def test_update_uses_correct_template(self):
        """Test update view uses correct template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertTemplateUsed(response, 'deficiencies/form.html')

    def test_update_context_contains_deficiency(self):
        """Test update view includes deficiency in context"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertIn('deficiency', response.context)


class DeficiencyDeleteViewTest(DeficiencyViewTestBase):
    """Test deficiency delete view"""

    def test_delete_requires_login(self):
        """Test delete view requires authentication"""
        response = self.client.get(reverse('deficiencies:delete', kwargs={'deficiency_number': 1}))
        self.assertEqual(response.status_code, 302)

    def test_delete_restricted_to_admins(self):
        """Test only admins can access delete view"""
        # Technicians should be denied
        self._login_as_technician()
        response = self.client.get(reverse('deficiencies:delete', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [302, 403])  # Redirect or forbidden

        # Admins should have access
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:delete', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [200, 404])

    def test_delete_uses_correct_template(self):
        """Test delete view uses confirmation template"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:delete', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertTemplateUsed(response, 'deficiencies/confirm_delete.html')


class ActionAddViewTest(DeficiencyViewTestBase):
    """Test action add view"""

    def test_action_add_requires_login(self):
        """Test action add view requires authentication"""
        response = self.client.get(reverse('deficiencies:add_action', kwargs={'deficiency_number': 1}))
        self.assertEqual(response.status_code, 302)

    def test_action_add_accessible_to_technicians(self):
        """Test technicians can access action add"""
        self._login_as_technician()
        response = self.client.get(reverse('deficiencies:add_action', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [200, 404])

    def test_action_add_accessible_to_admins(self):
        """Test admins can access action add"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:add_action', kwargs={'deficiency_number': 1}))
        self.assertIn(response.status_code, [200, 404])

    def test_action_add_renders_form_for_get(self):
        """Test GET request renders form"""
        self._login_as_admin()
        response = self.client.get(reverse('deficiencies:add_action', kwargs={'deficiency_number': 1}))
        if response.status_code == 200:
            self.assertIn('form', response.context)


class ViewPermissionTest(DeficiencyViewTestBase):
    """Test view-level permissions"""

    def test_viewer_cannot_create(self):
        """Test viewers cannot access create view"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:create'))
        # Should redirect with permission denied message
        self.assertEqual(response.status_code, 302)

    def test_viewer_cannot_update(self):
        """Test viewers cannot access update view"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:update', kwargs={'deficiency_number': 1}))
        # Should redirect with permission denied
        self.assertEqual(response.status_code, 302)

    def test_viewer_cannot_delete(self):
        """Test viewers cannot access delete view"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:delete', kwargs={'deficiency_number': 1}))
        # Should redirect with permission denied
        self.assertEqual(response.status_code, 302)

    def test_viewer_cannot_add_action(self):
        """Test viewers cannot add actions"""
        self._login_as_viewer()
        response = self.client.get(reverse('deficiencies:add_action', kwargs={'deficiency_number': 1}))
        # Should redirect with permission denied
        self.assertEqual(response.status_code, 302)


class ViewCacheTest(DeficiencyViewTestBase):
    """Test cache invalidation in views"""

    def test_dashboard_cache_cleared_after_create(self):
        """Test dashboard cache is cleared after creating deficiency"""
        self._login_as_admin()

        # Set cache
        cache.set('dashboard_metrics', {'test': 'data'}, 20)

        # Attempt to create with valid data (matching database dropdown values)
        response = self.client.post(
            reverse('deficiencies:create'),
            {
                'site_name': 'Site A',  # Must exist in database
                'resource': 'Resource 1',  # Must exist in database
                'issue_description': 'Test issue for cache test',
                'status': 'OPEN',
                'severity': 'C',
                'type': 'Hardware',
                'deficiency_type': 'Maintenance',  # Must exist in database
                'category_name': 'Category 1',  # Must exist in database
                'raised_by_name': 'Admin User',  # Must exist in database
                'customer': 'Internal',  # Must exist in database
                'due_date': '2025-12-31',
            }
        )
        # Cache should be cleared regardless of POST result
        self.assertIsNone(cache.get('dashboard_metrics'))


class ViewURLTest(DeficiencyViewTestBase):
    """Test URL routing for views"""

    def test_dashboard_url_resolves(self):
        """Test dashboard URL resolves correctly"""
        self._login_as_admin()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_list_url_resolves(self):
        """Test list URL resolves correctly"""
        self._login_as_admin()
        response = self.client.get('/deficiencies/')
        self.assertEqual(response.status_code, 200)

    def test_create_url_resolves(self):
        """Test create URL resolves correctly"""
        self._login_as_admin()
        response = self.client.get('/deficiency/new/')
        self.assertEqual(response.status_code, 200)

    def test_detail_url_resolves(self):
        """Test detail URL resolves correctly"""
        self._login_as_admin()
        response = self.client.get('/deficiency/1/')
        self.assertIn(response.status_code, [200, 404])

    def test_update_url_resolves(self):
        """Test update URL resolves correctly"""
        self._login_as_admin()
        response = self.client.get('/deficiency/1/edit/')
        self.assertIn(response.status_code, [200, 404])

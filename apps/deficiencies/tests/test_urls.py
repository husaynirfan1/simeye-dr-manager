"""
Unit tests for URL routing in deficiencies app.
"""
from django.test import TestCase
from django.urls import reverse, resolve
from django.urls.exceptions import Resolver404

from apps.deficiencies import views
from .test_config import DeficiencyTestCase


class DeficienciesURLTest(DeficiencyTestCase):
    """Test URL routing for deficiencies app"""

    def test_app_name(self):
        """Test app namespace is set correctly"""
        from apps.deficiencies import urls
        self.assertEqual(urls.app_name, 'deficiencies')

    def test_dashboard_url_reverses(self):
        """Test dashboard URL name reverses correctly"""
        url = reverse('deficiencies:dashboard')
        self.assertEqual(url, '/')

    def test_dashboard_url_resolves(self):
        """Test dashboard URL resolves to correct view"""
        url = '/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.dashboard)

    def test_list_url_reverses(self):
        """Test list URL name reverses correctly"""
        url = reverse('deficiencies:list')
        self.assertEqual(url, '/deficiencies/')

    def test_list_url_resolves(self):
        """Test list URL resolves to correct view"""
        url = '/deficiencies/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_list)

    def test_create_url_reverses(self):
        """Test create URL name reverses correctly"""
        url = reverse('deficiencies:create')
        self.assertEqual(url, '/deficiency/new/')

    def test_create_url_resolves(self):
        """Test create URL resolves to correct view"""
        url = '/deficiency/new/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_create)

    def test_detail_url_reverses_with_pk(self):
        """Test detail URL name reverses correctly with pk"""
        url = reverse('deficiencies:detail', kwargs={'deficiency_number': 123})
        self.assertEqual(url, '/deficiency/123/')

    def test_detail_url_resolves(self):
        """Test detail URL resolves to correct view"""
        url = '/deficiency/123/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_detail)
        # Check the pk is captured correctly
        self.assertEqual(resolved.kwargs['deficiency_number'], 123)

    def test_update_url_reverses_with_pk(self):
        """Test update URL name reverses correctly with pk"""
        url = reverse('deficiencies:update', kwargs={'deficiency_number': 456})
        self.assertEqual(url, '/deficiency/456/edit/')

    def test_update_url_resolves(self):
        """Test update URL resolves to correct view"""
        url = '/deficiency/456/edit/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_update)
        self.assertEqual(resolved.kwargs['deficiency_number'], 456)

    def test_delete_url_reverses_with_pk(self):
        """Test delete URL name reverses correctly with pk"""
        url = reverse('deficiencies:delete', kwargs={'deficiency_number': 789})
        self.assertEqual(url, '/deficiency/789/delete/')

    def test_delete_url_resolves(self):
        """Test delete URL resolves to correct view"""
        url = '/deficiency/789/delete/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_delete)
        self.assertEqual(resolved.kwargs['deficiency_number'], 789)

    def test_add_action_url_reverses_with_pk(self):
        """Test add_action URL name reverses correctly with pk"""
        url = reverse('deficiencies:add_action', kwargs={'deficiency_number': 999})
        self.assertEqual(url, '/deficiency/999/action/')

    def test_add_action_url_resolves(self):
        """Test add_action URL resolves to correct view"""
        url = '/deficiency/999/action/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.action_add)
        self.assertEqual(resolved.kwargs['deficiency_number'], 999)


class URLPatternOrderTest(DeficiencyTestCase):
    """Test URL pattern ordering to prevent conflicts"""

    def test_create_url_before_detail(self):
        """Test create URL pattern is before detail to prevent interception"""
        from apps.deficiencies.urls import urlpatterns
        # Find the positions of create and detail patterns
        create_position = None
        detail_position = None

        for i, pattern in enumerate(urlpatterns):
            if hasattr(pattern, 'name'):
                if pattern.name == 'create':
                    create_position = i
                elif pattern.name == 'detail':
                    detail_position = i

        # Create should come before detail
        self.assertIsNotNone(create_position, "Create URL pattern not found")
        self.assertIsNotNone(detail_position, "Detail URL pattern not found")
        self.assertLess(create_position, detail_position,
                        "Create URL should be defined before detail URL")


class URLParameterTest(DeficiencyTestCase):
    """Test URL parameter handling"""

    def test_detail_url_requires_integer(self):
        """Test detail URL requires integer deficiency_number"""
        # Should not match non-numeric values
        url = '/deficiency/abc/'
        with self.assertRaises(Resolver404):
            resolve(url)

    def test_update_url_requires_integer(self):
        """Test update URL requires integer deficiency_number"""
        url = '/deficiency/abc/edit/'
        with self.assertRaises(Resolver404):
            resolve(url)

    def test_delete_url_requires_integer(self):
        """Test delete URL requires integer deficiency_number"""
        url = '/deficiency/abc/delete/'
        with self.assertRaises(Resolver404):
            resolve(url)

    def test_add_action_url_requires_integer(self):
        """Test add_action URL requires integer deficiency_number"""
        url = '/deficiency/abc/action/'
        with self.assertRaises(Resolver404):
            resolve(url)

    def test_detail_url_with_large_number(self):
        """Test detail URL handles large numbers"""
        url = '/deficiency/999999/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_detail)
        self.assertEqual(resolved.kwargs['deficiency_number'], 999999)

    def test_detail_url_with_zero(self):
        """Test detail URL handles zero"""
        url = '/deficiency/0/'
        resolved = resolve(url)
        self.assertEqual(resolved.func, views.deficiency_detail)
        self.assertEqual(resolved.kwargs['deficiency_number'], 0)


class URLTrailingSlashTest(DeficiencyTestCase):
    """Test URL trailing slash handling"""

    def test_dashboard_url_with_trailing_slash(self):
        """Test dashboard URL works with trailing slash"""
        url = reverse('deficiencies:dashboard')
        self.assertTrue(url.endswith('/'))

    def test_list_url_with_trailing_slash(self):
        """Test list URL works with trailing slash"""
        url = reverse('deficiencies:list')
        self.assertTrue(url.endswith('/'))

    def test_create_url_with_trailing_slash(self):
        """Test create URL works with trailing slash"""
        url = reverse('deficiencies:create')
        self.assertTrue(url.endswith('/'))

    def test_detail_url_with_trailing_slash(self):
        """Test detail URL works with trailing slash"""
        url = reverse('deficiencies:detail', kwargs={'deficiency_number': 1})
        self.assertTrue(url.endswith('/'))

    def test_update_url_with_trailing_slash(self):
        """Test update URL works with trailing slash"""
        url = reverse('deficiencies:update', kwargs={'deficiency_number': 1})
        self.assertTrue(url.endswith('/'))

    def test_delete_url_with_trailing_slash(self):
        """Test delete URL works with trailing slash"""
        url = reverse('deficiencies:delete', kwargs={'deficiency_number': 1})
        self.assertTrue(url.endswith('/'))

    def test_add_action_url_with_trailing_slash(self):
        """Test add_action URL works with trailing slash"""
        url = reverse('deficiencies:add_action', kwargs={'deficiency_number': 1})
        self.assertTrue(url.endswith('/'))


class URLNameConflictTest(DeficiencyTestCase):
    """Test for potential URL name conflicts"""

    def test_all_url_names_are_unique(self):
        """Test all URL names in the app are unique"""
        from apps.deficiencies.urls import urlpatterns
        names = []
        for pattern in urlpatterns:
            if hasattr(pattern, 'name') and pattern.name:
                names.append(pattern.name)

        # Check for duplicates
        self.assertEqual(len(names), len(set(names)),
                        "URL names should be unique. Found duplicates: " +
                        ", ".join([name for name in names if names.count(name) > 1]))

    def test_expected_url_names_exist(self):
        """Test all expected URL names are defined"""
        expected_names = [
            'dashboard', 'list', 'create', 'detail',
            'update', 'delete', 'add_action'
        ]

        from apps.deficiencies.urls import urlpatterns
        defined_names = []
        for pattern in urlpatterns:
            if hasattr(pattern, 'name') and pattern.name:
                defined_names.append(pattern.name)

        for name in expected_names:
            self.assertIn(name, defined_names,
                          f"Expected URL name '{name}' not found in urlpatterns")

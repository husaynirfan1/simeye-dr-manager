"""
Authentication and permission mixins for views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin requiring admin role"""
    def test_func(self):
        return self.request.user.has_full_access()


class TechnicianRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin requiring technician or admin role"""
    def test_func(self):
        return self.request.user.can_edit_deficiency()


class ViewerRequiredMixin(LoginRequiredMixin):
    """Mixin requiring any logged-in user"""
    pass


def check_permission(user, required_permission):
    """
    Check if user has a specific permission.
    Usage in views: @permission_required('deficiencies.view_deficiency')
    """
    if not user.has_perm(required_permission):
        raise PermissionDenied
    return True

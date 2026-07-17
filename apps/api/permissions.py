"""
Custom permissions for API endpoints.
"""
from rest_framework import permissions


class IsViewerOrAbove(permissions.IsAuthenticated):
    """
    Allows access to all authenticated users (Viewers, Technicians, Admins).
    """
    pass


class IsTechnicianOrAbove(permissions.BasePermission):
    """
    Allows access only to Technicians and Admins.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.can_edit_deficiency()
        )


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to Admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_full_access()
        )

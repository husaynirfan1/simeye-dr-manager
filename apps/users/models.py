"""
Custom User model with role-based permissions.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    """User role choices for deficiency management system"""
    ADMIN = 'ADMIN', _('Admin')
    TECHNICIAN = 'TECHNICIAN', _('Technician')
    VIEWER = 'VIEWER', _('Viewer')


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser with role-based permissions.
    Roles:
    - ADMIN: Full access to all features and Django admin
    - TECHNICIAN: Read/write access to deficiency database only
    - VIEWER: Read-only access (for future use)
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER,
        verbose_name=_('Role')
    )

    class Meta:
        db_table = 'dr_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        permissions = [
            ("full_access", "Full administrative access"),
            ("read_write_dr", "Read/write access to deficiency database"),
            ("view_only", "View only access"),
        ]

    def __str__(self):
        return f"{self.get_username()} ({self.get_role_display()})"

    def has_full_access(self):
        """Check if user has admin role with full access"""
        return self.role == UserRole.ADMIN

    def can_edit_deficiency(self):
        """Check if user can edit deficiencies (Admin or Technician)"""
        return self.role in [UserRole.ADMIN, UserRole.TECHNICIAN]

    def can_view_dashboard(self):
        """Check if user can view dashboard (all authenticated users)"""
        return self.is_authenticated

    def can_edit_journey_logs(self):
        """Check if user can edit journey logs (Admin or Technician)"""
        return self.role in [UserRole.ADMIN, UserRole.TECHNICIAN]

    def can_view_schedule(self):
        """Check if user can view schedule (Admin or Technician)"""
        return self.role in [UserRole.ADMIN, UserRole.TECHNICIAN]


class UserProfile(models.Model):
    """
    Extended profile information for users.
    Can be used for future enhancements like preferences, notifications, etc.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('User')
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dr_user_profile'
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')

    def __str__(self):
        return f"{self.user.username}'s profile"

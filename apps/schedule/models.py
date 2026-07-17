"""
Models for schedule management.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class ScheduleSession(models.Model):
    """Training schedule session slots"""
    session_date = models.DateField(
        verbose_name=_('Session Date')
    )
    time_slot = models.CharField(
        max_length=20,
        verbose_name=_('Time Slot')
    )
    end_time = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('End Time')
    )
    resource = models.CharField(
        max_length=50,
        default='AW139',
        verbose_name=_('Resource')
    )
    customer = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Customer')
    )
    is_booked = models.BooleanField(
        default=False,
        verbose_name=_('Is Booked')
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name=_('Is Completed')
    )
    journey_log = models.OneToOneField(
        'journey_logs.JourneyLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_slot',
        verbose_name=_('Journey Log')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'dr_schedule_sessions'
        managed = False  # Use existing table
        unique_together = [['session_date', 'time_slot', 'resource']]
        ordering = ['session_date', 'time_slot']
        verbose_name = _('Schedule Session')
        verbose_name_plural = _('Schedule Sessions')

    def __str__(self):
        return f"{self.session_date} {self.time_slot} - {self.customer or 'Available'}"

    @property
    def is_available(self):
        """Check if slot is available for booking"""
        return not self.is_completed

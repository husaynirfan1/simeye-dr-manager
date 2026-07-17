"""
Models for journey log tracking.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class JourneyLog(models.Model):
    """Journey/training log for sessions"""
    customer_name = models.CharField(
        max_length=255,
        verbose_name=_('Customer Name')
    )
    log_date = models.DateField(
        verbose_name=_('Log Date')
    )
    site = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Site')
    )
    resource_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Resource Type')
    )
    resource = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Resource')
    )
    session_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Session Type')
    )
    training_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Training Type')
    )
    report_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Report By')
    )
    schedule_slot_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Schedule Slot ID')
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
        db_table = 'dr_journey_log'
        managed = False  # Use existing table
        ordering = ['-log_date', '-created_at']
        verbose_name = _('Journey Log')
        verbose_name_plural = _('Journey Logs')

    def __str__(self):
        return f"Journey Log {self.id} - {self.customer_name} ({self.log_date})"

    @property
    def linked_dr_count(self):
        """Count of linked deficiencies"""
        return self.linked_deficiencies.count()

    @property
    def crew_members(self):
        """Get crew members for this journey log"""
        return self.crew_set.all()

    @property
    def linked_deficiencies(self):
        """Get linked deficiencies"""
        return self.dr_links.all()


class JourneyLogCrew(models.Model):
    """Crew members for journey logs"""
    journey_log = models.ForeignKey(
        JourneyLog,
        on_delete=models.CASCADE,
        related_name='crew_set',
        verbose_name=_('Journey Log')
    )
    crew_name = models.CharField(
        max_length=255,
        verbose_name=_('Crew Name')
    )
    license_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('License Number')
    )
    crew_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Crew Type')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    class Meta:
        db_table = 'dr_journey_log_crew'
        managed = False  # Use existing table
        verbose_name = _('Journey Log Crew')
        verbose_name_plural = _('Journey Log Crew Members')

    def __str__(self):
        return f"{self.crew_name} - {self.journey_log}"


class JourneyLogDR(models.Model):
    """Link table between Journey Logs and Deficiencies"""
    journey_log = models.ForeignKey(
        JourneyLog,
        on_delete=models.CASCADE,
        related_name='dr_links',
        verbose_name=_('Journey Log')
    )
    deficiency_number = models.IntegerField(
        verbose_name=_('Deficiency Number')
    )
    linked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Linked At')
    )

    class Meta:
        db_table = 'dr_journey_log_dr'
        managed = False  # Use existing table
        unique_together = [['journey_log', 'deficiency_number']]
        verbose_name = _('Journey Log DR Link')
        verbose_name_plural = _('Journey Log DR Links')

    def __str__(self):
        return f"JL {self.journey_log_id} -> DR #{self.deficiency_number}"

    @property
    def deficiency(self):
        """Get the actual Deficiency object"""
        from apps.deficiencies.models import Deficiency
        try:
            return Deficiency.objects.get(pk=self.deficiency_number)
        except Deficiency.DoesNotExist:
            return None

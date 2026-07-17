"""
Models for deficiency tracking system.
Uses existing database tables with managed=False to avoid schema changes.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

class DeficiencyQuerySet(models.QuerySet):
    """Custom queryset for Deficiency model with common filters"""

    def open(self):
        return self.filter(status='OPEN')

    def in_work(self):
        return self.filter(status='In Work')

    def cleared(self):
        return self.filter(status__in=['Cleared', 'CLOSED'])

    def high_severity(self):
        return self.filter(severity='A')

    def by_site(self, site):
        return self.filter(site_name=site)

    def by_resource(self, resource):
        return self.filter(resource=resource)

    def search(self, query):
        """Search across multiple fields"""
        from django.db.models import Q
        return self.filter(
            Q(deficiency_number__icontains=query) |
            Q(site_name__icontains=query) |
            Q(resource__icontains=query) |
            Q(issue_description__icontains=query) |
            Q(raised_by_name__icontains=query)
        )


class DeficiencyManager(models.Manager):
    """Custom manager for Deficiency model"""

    def get_queryset(self):
        return DeficiencyQuerySet(self.model, using=self._db)

    def open(self):
        return self.get_queryset().open()

    def in_work(self):
        return self.get_queryset().in_work()

    def cleared(self):
        return self.get_queryset().cleared()

    def high_severity(self):
        return self.get_queryset().high_severity()

    def statistics(self):
        """Get deficiency statistics"""
        from django.db.models import Count
        return self.aggregate(
            total=Count('deficiency_number'),
            open_count=Count('deficiency_number', filter=models.Q(status='OPEN')),
            in_work_count=Count('deficiency_number', filter=models.Q(status='In Work')),
            cleared_count=Count('deficiency_number', filter=models.Q(status__in=['Cleared', 'CLOSED'])),
        )


class Deficiency(models.Model):
    """
    Deficiency tracking model - maps to existing dr_deficiency table.
    Using managed=False to use existing database schema.
    """

    # Identity fields
    deficiency_number = models.IntegerField(
        primary_key=True,
        verbose_name=_('Deficiency Number'),
        db_column='"DeficiencyNumber"'
    )
    site_name = models.CharField(
        max_length=100,
        verbose_name=_('Site Name'),
        db_column='"SiteName"'
    )
    resource = models.CharField(
        max_length=100,
        verbose_name=_('Resource'),
        db_column='"Resource"'
    )
    issue_description = models.TextField(
        verbose_name=_('Issue Description'),
        db_column='"Issue_Description"'
    )

    # Status fields
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('In Work', 'In Work'),
        ('Monitoring', 'Monitoring'),
        ('On Offer', 'On Offer'),
        ('On Hold', 'On Hold'),
        ('Cleared', 'Cleared'),
        ('CLOSED', 'Closed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN',
        verbose_name=_('Status'),
        db_column='"Status"'
    )

    SEVERITY_CHOICES = [
        ('A', 'A - Critical'),
        ('B', 'B - Major'),
        ('C', 'C - Minor'),
        ('D', 'D - Cosmetic'),
    ]
    severity = models.CharField(
        max_length=1,
        choices=SEVERITY_CHOICES,
        default='C',
        verbose_name=_('Severity'),
        db_column='"Severity"'
    )
    sub_status_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Sub Status'),
        db_column='"SubStatusName"'
    )
    type = models.CharField(
        max_length=50,
        default='Hardware',
        verbose_name=_('Type'),
        db_column='"Type"'
    )
    deficiency_type = models.CharField(
        max_length=50,
        default='Maintenance',
        verbose_name=_('Deficiency Type'),
        db_column='"DeficiencyType"'
    )
    category_name = models.CharField(
        max_length=100,
        default='General',
        verbose_name=_('Category'),
        db_column='"CategoryName"'
    )

    # People fields
    raised_by_name = models.CharField(
        max_length=255,
        default='System',
        verbose_name=_('Raised By'),
        db_column='"RaisedByName"'
    )
    assignee_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Assignee'),
        db_column='"AssigneeName"'
    )
    assignee_group_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Assignee Group'),
        db_column='"AssigneeGroupName"'
    )
    entered_by_name = models.CharField(
        max_length=255,
        default='System',
        verbose_name=_('Entered By'),
        db_column='"EnteredByName"'
    )
    cleared_by_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Cleared By'),
        db_column='"ClearedbyName"'
    )

    # Date fields - database stores YYYY-MM-DD, displayed as DD-MM-YYYY
    raised_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Raised Date'),
        db_column='"RaisedDate"'
    )
    entered_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Entered Date'),
        db_column='"EnteredDate"'
    )
    cleared_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Cleared Date'),
        db_column='"ClearedDate"'
    )
    due_date = models.DateField(
        blank=True,  # Allow blank in forms, but DB requires NOT NULL
        verbose_name=_('Due Date'),
        db_column='"DueDate"'
    )
    naa_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('NAA Due Date'),
        db_column='"NAADueDate"'
    )
    on_offer_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('On Offer Date'),
        db_column='"OnOfferDate"'
    )

    # Timestamp fields (for exact tracking)
    _raised_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column='"_RaisedDate"'
    )
    _entered_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column='"_EnteredDate"'
    )
    _cleared_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column='"_ClearedDate"'
    )
    _due_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column='"_DueDate"'
    )

    # fld* date columns (preserve for compatibility)
    fld_raised_date = models.DateField(
        null=True,
        blank=True,
        db_column='"fldRaisedDate"'
    )
    fld_due_date = models.DateField(
        null=True,
        blank=True,
        db_column='"fldDueDate"'
    )
    fld_last_action_taken_date = models.DateField(
        null=True,
        blank=True,
        db_column='"fldLastActionTakenDate"'
    )

    # Numeric fields
    downtime = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Down Time'),
        db_column='"DownTime"'
    )
    interrupt_minutes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Interrupt Minutes'),
        db_column='"InterruptMinutes"'
    )
    device_interrupt_minutes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Device Interrupt Minutes'),
        db_column='"DeviceInterruptMinutes"'
    )

    # Boolean flags
    is_restricted = models.BooleanField(
        default=False,
        verbose_name=_('Is Restricted'),
        db_column='"Is_Restricted"'
    )
    is_safety = models.BooleanField(
        default=False,
        verbose_name=_('Is Safety'),
        db_column='"Is_Safety"'
    )
    affects_qualification = models.BooleanField(
        default=False,
        verbose_name=_('Affects Qualification'),
        db_column='"Affects_Qualification"'
    )
    dashboard_visible = models.BooleanField(
        default=True,
        verbose_name=_('Dashboard Visible'),
        db_column='"DashboardVisible"'
    )

    # Optional fields
    spr = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column='"SPR"'
    )
    tracking_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column='"TrackingNumber"'
    )
    system = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='"System"'
    )
    sub_system = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='"SubSystem"'
    )
    conversion = models.TextField(
        null=True,
        blank=True,
        db_column='"Conversion"'
    )
    configuration = models.TextField(
        null=True,
        blank=True,
        db_column='"Configuration"'
    )
    restriction = models.TextField(
        null=True,
        blank=True,
        db_column='"Restriction"'
    )
    alternate_method = models.TextField(
        null=True,
        blank=True,
        db_column='"AlternateMethod"'
    )
    customer = models.CharField(
        max_length=255,
        default='Internal',
        db_column='"Customer"'
    )

    fld_resource_id = models.IntegerField(
        default=1,
        db_column='"fldResourceId"'
    )
    fld_raised_by_id = models.IntegerField(
        default=1,
        db_column='"fldRaisedById"'
    )
    fld_entered_by_id = models.IntegerField(
        default=1,
        db_column='"fldEnteredById"'
    )

    # Legacy actiontaken field (will be deprecated after migration)
    actiontaken = models.TextField(
        null=True,
        blank=True,
        db_column='"ActionTaken"'
    )

    objects = DeficiencyManager()

    # --- ADD THIS SELF-HEALING INTERCEPTOR ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import datetime

        # Every single date field in your legacy database
        date_fields = [
            'raised_date', 'entered_date', 'cleared_date', 'due_date',
            'naa_due_date', 'on_offer_date', 'fld_raised_date',
            'fld_due_date', 'fld_last_action_taken_date'
        ]

        for field in date_fields:
            val = getattr(self, field, None)

            # If the database gave us a string instead of a proper date
            if isinstance(val, str) and val.strip():
                # Try multiple date formats that might exist in the legacy database
                # Order matters: try most likely formats first
                # 1. YYYY-MM-DD (standard Django format - check first)
                # 2. MM/DD/YYYY (US format from browser locale)
                # 3. DD/MM/YYYY (UK/Australian format)
                # 4. DD-MM-YYYY (European format with dashes)
                # 5. DD-MMM-YYYY (legacy Oracle format e.g., "07-JUN-2026")
                formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y']

                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(val.strip().upper(), fmt)
                        # Overwrite it with the clean YYYY-MM-DD format Django expects
                        setattr(self, field, parsed_date.strftime('%Y-%m-%d'))
                        break  # Successfully parsed, move to next field
                    except ValueError:
                        continue  # Try next format

    class Meta:
        db_table = 'dr_deficiency'
        managed = False  # Use existing table, don't create
        ordering = ['-deficiency_number']
        verbose_name = _('Deficiency')
        verbose_name_plural = _('Deficiencies')

    def __str__(self):
        return f"DR#{self.deficiency_number} - {self.issue_description[:50]}"

    def get_absolute_url(self):
        """Get URL for viewing this deficiency"""
        from django.urls import reverse
        return reverse('deficiencies:detail', kwargs={'pk': self.deficiency_number})

    @property
    def parsed_actions(self):
        """
        Parse ActionTaken text into list of action dictionaries.
        Returns empty list if actiontaken is None or empty.
        """
        if not self.actiontaken:
            return []

        import re
        actions = []
        # Split by carriage return or similar separators
        entries = re.split(r'(?:&#x0D;|\r\n|\n)', self.actiontaken)

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            # Parse the entry - format: [date] [user] [description]
            match = re.match(r'\[([^\]]+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]', entry)
            if match:
                actions.append({
                    'timestamp': match.group(1),
                    'username': match.group(2),
                    'description': match.group(3),
                    'full': entry
                })

        return actions

    def format_date(self, date_field):
        """
        Format a date field for display in DD-MM-YYYY format.
        Returns None if the date is None or empty.
        """
        date_value = getattr(self, date_field, None)
        if date_value:
            try:
                if isinstance(date_value, str):
                    # If it's already a string, try to parse and format
                    from datetime import datetime
                    # Try YYYY-MM-DD format first
                    try:
                        date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                    except ValueError:
                        # Try DD-MMM-YYYY format
                        date_obj = datetime.strptime(date_value, '%d-%b-%Y')
                    return date_obj.strftime('%d-%m-%Y')
                else:
                    # It's a date/datetime object
                    return date_value.strftime('%d-%m-%Y')
            except (ValueError, AttributeError, TypeError):
                return str(date_value) if date_value else None
        return None

    @property
    def due_date_display(self):
        """Return due date in DD-MM-YYYY format for display"""
        return self.format_date('due_date')

    @property
    def raised_date_display(self):
        """Return raised date in DD-MM-YYYY format for display"""
        return self.format_date('raised_date')

    @property
    def cleared_date_display(self):
        """Return cleared date in DD-MM-YYYY format for display"""
        return self.format_date('cleared_date')

    @property
    def entered_date_display(self):
        """Return entered date in DD-MM-YYYY format for display"""
        return self.format_date('entered_date')
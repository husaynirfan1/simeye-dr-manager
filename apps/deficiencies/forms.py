"""
Django Forms for deficiency management.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Deficiency
from django.utils import timezone
from datetime import timedelta, datetime
from .utility import normalize_date


class DateInput(forms.DateInput):
    """Custom DateInput that handles legacy date formats from database"""

    def format_value(self, value):
        if value is None:
            return ''
        if isinstance(value, str):
            # Try to normalize the date string
            normalized = normalize_date(value)
            if normalized:
                # If normalize returned a date object, format it
                if hasattr(normalized, 'strftime'):
                    return normalized.strftime('%Y-%m-%d')
                # If it's still a string in YYYY-MM-DD format, return as-is
                if '/' in value:  # Legacy DD/MM/YYYY format
                    try:
                        # Try to parse and convert
                        for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                            try:
                                parsed = datetime.strptime(value.strip(), fmt)
                                return parsed.strftime('%Y-%m-%d')
                            except ValueError:
                                continue
                    except:
                        pass
            return value
        # For date/datetime objects, use default formatting
        return super().format_value(value)

class DeficiencyForm(forms.ModelForm):
    """Form for creating/editing deficiencies"""
    def __init__(self, *args, **kwargs):
        # Extract the user before initializing the form
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        # 1. Fetch all existing names and turn this field into a dropdown
        existing_names = Deficiency.objects.exclude(raised_by_name__exact='').exclude(raised_by_name__isnull=True).values_list('raised_by_name', flat=True).distinct().order_by('raised_by_name')
        choices = [('', 'Select a name...')] + [(name, name) for name in existing_names]
        
        self.fields['raised_by_name'] = forms.ChoiceField(
            choices=choices,
            required=False,  # Must be false because disabled fields don't submit data!
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        # 1. Fetch clean, unique lists from the database
        sites = Deficiency.objects.exclude(site_name__isnull=True).exclude(site_name__exact='').values_list('site_name', flat=True).distinct().order_by('site_name')
        resources = Deficiency.objects.exclude(resource__isnull=True).exclude(resource__exact='').values_list('resource', flat=True).distinct().order_by('resource')
        categories = Deficiency.objects.exclude(category_name__isnull=True).exclude(category_name__exact='').values_list('category_name', flat=True).distinct().order_by('category_name')
        def_types = Deficiency.objects.exclude(deficiency_type__isnull=True).exclude(deficiency_type__exact='').values_list('deficiency_type', flat=True).distinct().order_by('deficiency_type')
        customers = Deficiency.objects.exclude(customer__isnull=True).exclude(customer__exact='').values_list('customer', flat=True).distinct().order_by('customer')

        # 2. Force the fields to be ChoiceFields with the 'form-select' dropdown UI
        self.fields['site_name'] = forms.ChoiceField(
            choices=[('', 'Select Site...')] + [(x, x) for x in sites],
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        self.fields['resource'] = forms.ChoiceField(
            choices=[('', 'Select Resource...')] + [(x, x) for x in resources],
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        self.fields['category_name'] = forms.ChoiceField(
            choices=[('', 'Select Category...')] + [(x, x) for x in categories],
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        self.fields['deficiency_type'] = forms.ChoiceField(
            choices=[('', 'Select Type...')] + [(x, x) for x in def_types],
            required=False, # Make True if it is mandatory!
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        
        self.fields['customer'] = forms.ChoiceField(
            choices=[('', 'Select Customer...')] + [(x, x) for x in customers],
            required=False, # Make True if it is mandatory!
            widget=forms.Select(attrs={'class': 'form-select'})
        )

        # 2. UI Logic based on role
        if self.user:
            user_name = self.user.get_full_name() or self.user.username
            
            if not self.user.has_full_access():
                # Regular Tech: Force their name and grey it out
                self.initial['raised_by_name'] = user_name
                self.fields['raised_by_name'].widget.attrs['disabled'] = 'disabled'
            else:
                # Admin: Leave it enabled, but default to their name if it's a new form
                if not self.initial.get('raised_by_name'):
                    self.initial['raised_by_name'] = user_name
        # Set smart defaults if this is a BRAND NEW deficiency
        if not self.instance.pk:
            # Existing defaults
            self.initial['status'] = 'OPEN'
            self.initial['severity'] = 'D'

            # Auto-fill Due Date to 30 days from today
            future_date = timezone.now().date() + timedelta(days=30)
            self.initial['due_date'] = future_date.strftime('%Y-%m-%d')

    class Meta:
        model = Deficiency
        fields = [
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
        widgets = {
            # Textareas
            'issue_description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'conversion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'configuration': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'restriction': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'alternate_method': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            
            # Status & Severity Dropdowns
            'status': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),

            # Dates - using custom DateInput that handles legacy formats
            'due_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'naa_due_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'on_offer_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            
            # Standard Text Inputs
            'assignee_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter assignee name...'}),
            'assignee_group_name': forms.TextInput(attrs={'class': 'form-control'}),
            'spr': forms.TextInput(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Number Inputs
            'downtime': forms.NumberInput(attrs={'class': 'form-control'}),
            'interrupt_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'device_interrupt_minutes': forms.NumberInput(attrs={'class': 'form-control'}),

            # Checkboxes
            'dashboard_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_restricted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_safety': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'affects_qualification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_downtime(self):
        """Validate downtime is non-negative"""
        downtime = self.cleaned_data.get('downtime', 0)
        if downtime < 0:
            raise ValidationError(_('Downtime cannot be negative.'))
        return downtime

    def clean_interrupt_minutes(self):
        """Validate interrupt_minutes is non-negative"""
        interrupt_minutes = self.cleaned_data.get('interrupt_minutes', 0)
        if interrupt_minutes < 0:
            raise ValidationError(_('Interrupt minutes cannot be negative.'))
        return interrupt_minutes

    def clean_device_interrupt_minutes(self):
        """Validate device_interrupt_minutes is non-negative"""
        device_interrupt_minutes = self.cleaned_data.get('device_interrupt_minutes', 0)
        if device_interrupt_minutes < 0:
            raise ValidationError(_('Device interrupt minutes cannot be negative.'))
        return device_interrupt_minutes

    def clean_due_date(self):
        """Normalize due_date to handle DD/MM/YYYY and other date formats"""
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            return normalize_date(due_date)
        return due_date

    def clean_naa_due_date(self):
        """Normalize naa_due_date to handle DD/MM/YYYY and other date formats"""
        naa_due_date = self.cleaned_data.get('naa_due_date')
        if naa_due_date:
            return normalize_date(naa_due_date)
        return naa_due_date

    def clean_on_offer_date(self):
        """Normalize on_offer_date to handle DD/MM/YYYY and other date formats"""
        on_offer_date = self.cleaned_data.get('on_offer_date')
        if on_offer_date:
            return normalize_date(on_offer_date)
        return on_offer_date


class QuickFilterForm(forms.Form):
    """Form for filtering deficiencies"""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Deficiency.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    severity = forms.ChoiceField(
        choices=[('', 'All Severities')] + Deficiency.SEVERITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    site = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by site...'
        })
    )
    resource = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by resource...'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search all fields...'
        })
    )


class ActionAddForm(forms.Form):
    """Form for adding actions to deficiencies (manipulates actiontaken text)"""
    
    action_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Enter action description...'
        }),
        required=True
    )

    def __init__(self, *args, **kwargs):
        # Extract the user before initializing the form
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 1. Fetch all existing names from the database for the dropdown
        existing_names = Deficiency.objects.exclude(raised_by_name__exact='').exclude(raised_by_name__isnull=True).values_list('raised_by_name', flat=True).distinct().order_by('raised_by_name')
        choices = [('', 'Select a name...')] + [(name, name) for name in existing_names]

        # Create the dynamic dropdown field
        self.fields['username'] = forms.ChoiceField(
            choices=choices,
            required=False,  # Must be false because disabled fields don't submit data!
            widget=forms.Select(attrs={'class': 'form-select'})
        )

        # 2. UI Logic based on role
        if self.user:
            user_name = self.user.get_full_name() or self.user.username
            
            if not self.user.has_full_access():
                # Regular Tech: Force their name and grey it out
                self.initial['username'] = user_name
                self.fields['username'].widget.attrs['disabled'] = 'disabled'
            else:
                # Admin: Leave it enabled, default to their name
                self.initial['username'] = user_name


class DeficiencyBulkEditForm(forms.ModelForm):
    """Form for bulk editing deficiencies"""

    class Meta:
        model = Deficiency
        fields = ['status', 'severity', 'assignee_name']

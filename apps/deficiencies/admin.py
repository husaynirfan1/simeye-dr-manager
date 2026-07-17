"""
Django Admin configuration for Deficiency model.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Deficiency


@admin.register(Deficiency)
class DeficiencyAdmin(admin.ModelAdmin):
    """Admin configuration for Deficiency model"""
    list_display = [
        'deficiency_number', 'site_name', 'resource', 'status',
        'severity', 'raised_date', 'due_date'
    ]
    list_filter = ['status', 'severity', 'site_name', 'resource']
    search_fields = [
        'deficiency_number', 'issue_description', 'site_name',
        'resource', 'raised_by_name'
    ]
    readonly_fields = ('deficiency_number',)

    fieldsets = (
        (_('Identity'), {
            'fields': ('deficiency_number', 'site_name', 'resource', 'issue_description')
        }),
        (_('Status'), {
            'fields': ('status', 'severity', 'type', 'deficiency_type', 'category_name')
        }),
        (_('People'), {
            'fields': (
                'raised_by_name', 'assignee_name', 'assignee_group_name',
                'entered_by_name', 'cleared_by_name'
            )
        }),
        (_('Dates'), {
            'fields': (
                'raised_date', 'entered_date', 'cleared_date', 'due_date',
                'naa_due_date', 'on_offer_date'
            )
        }),
        (_('Flags'), {
            'fields': (
                'is_restricted', 'is_safety', 'affects_qualification',
                'dashboard_visible'
            )
        }),
        (_('Additional'), {
            'fields': (
                'spr', 'tracking_number', 'system', 'sub_system',
                'customer', 'downtime', 'interrupt_minutes', 'device_interrupt_minutes',
                'actiontaken'
            ),
            'classes': ('collapse',)
        }),
    )

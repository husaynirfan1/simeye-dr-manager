"""
Django Admin configuration for schedule models.
"""
from django.contrib import admin
from .models import ScheduleSession


@admin.register(ScheduleSession)
class ScheduleSessionAdmin(admin.ModelAdmin):
    """Admin configuration for ScheduleSession model"""
    list_display = [
        'session_date', 'time_slot', 'end_time', 'resource',
        'customer', 'is_booked', 'is_completed'
    ]
    list_filter = ['session_date', 'is_booked', 'is_completed', 'resource']
    search_fields = ['customer']
    date_hierarchy = 'session_date'

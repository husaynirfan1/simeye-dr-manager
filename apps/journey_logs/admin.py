"""
Django Admin configuration for journey log models.
"""
from django.contrib import admin
from .models import JourneyLog, JourneyLogCrew, JourneyLogDR


class JourneyLogCrewInline(admin.StackedInline):
    """Inline admin for crew members"""
    model = JourneyLogCrew
    extra = 0


class JourneyLogDRInline(admin.TabularInline):
    """Inline admin for linked DRs"""
    model = JourneyLogDR
    extra = 0
    readonly_fields = ('linked_at',)


@admin.register(JourneyLog)
class JourneyLogAdmin(admin.ModelAdmin):
    """Admin configuration for JourneyLog model"""
    list_display = ['id', 'customer_name', 'log_date', 'site', 'resource', 'created_at']
    list_filter = ['log_date', 'site', 'resource_type', 'session_type']
    search_fields = ['customer_name', 'report_by', 'site']
    inlines = [JourneyLogCrewInline, JourneyLogDRInline]


@admin.register(JourneyLogCrew)
class JourneyLogCrewAdmin(admin.ModelAdmin):
    """Admin configuration for JourneyLogCrew model"""
    list_display = ['journey_log', 'crew_name', 'crew_type', 'license_number']
    list_filter = ['crew_type']
    search_fields = ['crew_name', 'license_number']


@admin.register(JourneyLogDR)
class JourneyLogDRAdmin(admin.ModelAdmin):
    """Admin configuration for JourneyLogDR model"""
    list_display = ['journey_log', 'deficiency_number', 'linked_at']
    list_filter = ['linked_at']
    search_fields = ['deficiency_number']

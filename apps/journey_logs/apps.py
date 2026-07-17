"""
App configuration for journey logs app.
"""
from django.apps import AppConfig


class JourneyLogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.journey_logs'
    verbose_name = 'Journey Logs'

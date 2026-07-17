"""
App configuration for deficiencies app.
"""
from django.apps import AppConfig


class DeficienciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.deficiencies'
    verbose_name = 'Deficiencies'

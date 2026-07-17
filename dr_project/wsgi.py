"""
WSGI config for DR Deficiency Management System.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dr_project.settings.dev')
application = get_wsgi_application()

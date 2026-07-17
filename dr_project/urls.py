"""
URL configuration for DR Deficiency Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
handler503 = 'apps.core.views.custom_503'

urlpatterns = [
    path('', include('apps.users.urls')),
    path('admin/', admin.site.urls),
    path('', include('apps.deficiencies.urls')),
    path('journey-logs/', include('apps.journey_logs.urls')),
    path('schedule/', include('apps.schedule.urls')),
    path('api/', include('apps.api.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

"""
URL configuration for API app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeficiencyViewSet, JourneyLogViewSet

app_name = 'api'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'deficiencies', DeficiencyViewSet, basename='deficiency')
router.register(r'journey-logs', JourneyLogViewSet, basename='journey-log')

urlpatterns = [
    # Legacy API endpoints (matching Flask routes)
    path('search', DeficiencyViewSet.as_view({'get': 'search'}), name='search'),
    path('deficiency/<int:pk>', DeficiencyViewSet.as_view({'get': 'retrieve'}), name='deficiency_detail'),

    # DRF ViewSet URLs
    path('', include(router.urls)),
]

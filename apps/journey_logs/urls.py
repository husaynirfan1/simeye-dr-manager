"""
URL configuration for journey logs app.
"""
from django.urls import path
from . import views

app_name = 'journey_logs'

urlpatterns = [
    path('', views.journey_log_list, name='list'),
    path('new/', views.journey_log_create, name='create'),
    path('<int:pk>/', views.journey_log_detail, name='detail'),
    path('<int:pk>/edit/', views.journey_log_update, name='update'),
    path('<int:pk>/delete/', views.journey_log_delete, name='delete'),
    path('<int:pk>/generate/', views.journey_log_generate, name='generate'),
    path('<int:journey_log_id>/link-dr/', views.link_dr, name='link_dr'),
    path('<int:journey_log_id>/unlink-dr/<int:deficiency_number>/', views.unlink_dr, name='unlink_dr'),
]

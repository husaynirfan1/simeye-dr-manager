"""
URL configuration for schedule app.
"""
from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    path('', views.schedule_view, name='view'),
    path('book/', views.book_slot, name='book'),
    path('refresh/', views.refresh_schedule, name='refresh'),
]

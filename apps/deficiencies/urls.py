"""
URL configuration for deficiencies app.
"""
from django.urls import path
from . import views

app_name = 'deficiencies'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('deficiencies/', views.deficiency_list, name='list'),

    # Deficiency CRUD - using deficiency_number instead of pk
    
    # 1. MOVED 'new' to the top so it doesn't get intercepted!
    path('deficiency/new/', views.deficiency_create, name='create'),
    
    # 2. Changed 'str' to 'int' so these only trigger for numbers
    path('deficiency/<int:deficiency_number>/', views.deficiency_detail, name='detail'),
    path('deficiency/<int:deficiency_number>/edit/', views.deficiency_update, name='update'),
    path('deficiency/<int:deficiency_number>/delete/', views.deficiency_delete, name='delete'),

    # Actions
    path('deficiency/<int:deficiency_number>/action/', views.action_add, name='add_action'),
]
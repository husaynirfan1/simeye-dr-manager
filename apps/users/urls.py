"""
URL configuration for users app (login/logout views).
"""
from django.urls import path
from django.contrib.auth import views as auth_views

app_name = 'users'

urlpatterns = [
    # Using Django's built-in login/logout views
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
]

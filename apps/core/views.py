"""
Core views for shared functionality - error handlers, etc.
"""
from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponse


def custom_404(request, exception=None):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)


def custom_503(request):
    """Custom 503 Service Unavailable error handler"""
    return render(request, 'errors/503.html', status=503)

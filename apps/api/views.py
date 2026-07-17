"""
DRF API views for deficiency management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .serializers import (
    DeficiencySerializer, DeficiencyListSerializer,
    JourneyLogSerializer
)
from .permissions import IsViewerOrAbove, IsTechnicianOrAbove, IsAdminUser
from apps.deficiencies.models import Deficiency
from apps.journey_logs.models import JourneyLog


class DeficiencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for deficiency viewing.
    Provides list and detail views with filtering and search.
    """
    permission_classes = [IsViewerOrAbove]

    def get_serializer_class(self):
        """Use list serializer for list view"""
        if self.action == 'list':
            return DeficiencyListSerializer
        return DeficiencySerializer

    def get_queryset(self):
        """
        Optionally filter by status, severity, site, resource.
        Search across multiple fields if 'q' parameter provided.
        """
        queryset = Deficiency.objects.all()

        # Filter parameters
        status_filter = self.request.query_params.get('status')
        severity_filter = self.request.query_params.get('severity')
        site_filter = self.request.query_params.get('site')
        resource_filter = self.request.query_params.get('resource')
        search_query = self.request.query_params.get('q')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        if site_filter:
            queryset = queryset.filter(site_name=site_filter)
        if resource_filter:
            queryset = queryset.filter(resource=resource_filter)
        if search_query:
            queryset = queryset.filter(
                Q(deficiency_number__icontains=search_query) |
                Q(site_name__icontains=search_query) |
                Q(resource__icontains=search_query) |
                Q(issue_description__icontains=search_query) |
                Q(raised_by_name__icontains=search_query)
            )

        return queryset.order_by('-deficiency_number')

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search endpoint: /api/search?q=query&field=field
        field can be: all, deficiency_number, site, resource
        """
        search = request.query_params.get('q', '')
        field = request.query_params.get('field', 'all')

        if not search:
            return Response({'results': []})

        queryset = Deficiency.objects.all()

        if field == 'deficiency_number':
            queryset = queryset.filter(deficiency_number__icontains=search)
        elif field == 'site':
            queryset = queryset.filter(site_name__icontains=search)
        elif field == 'resource':
            queryset = queryset.filter(resource__icontains=search)
        else:  # 'all' or any other value
            queryset = queryset.filter(
                Q(deficiency_number__icontains=search) |
                Q(site_name__icontains=search) |
                Q(resource__icontains=search) |
                Q(issue_description__icontains=search)
            )

        results = list(queryset[:20].values(
            'deficiency_number', 'site_name', 'resource',
            'issue_description', 'status'
        ))

        return Response({'results': results})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get deficiency statistics"""
        from django.db.models import Count

        stats = {
            'by_status': list(Deficiency.objects.values('status').annotate(
                count=Count('deficiency_number')
            ).order_by('-count')),
            'by_severity': list(Deficiency.objects.values('severity').annotate(
                count=Count('deficiency_number')
            ).order_by('-count')),
            'total': Deficiency.objects.count()
        }
        return Response(stats)


class JourneyLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for journey log viewing"""
    serializer_class = JourneyLogSerializer
    permission_classes = [IsViewerOrAbove]

    def get_queryset(self):
        return JourneyLog.objects.all().order_by('-log_date', '-created_at')

"""
DRF Serializers for API endpoints.
"""
from rest_framework import serializers
from apps.deficiencies.models import Deficiency
from apps.journey_logs.models import JourneyLog


class DeficiencySerializer(serializers.ModelSerializer):
    """Serializer for Deficiency model with actiontaken"""
    parsed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Deficiency
        fields = [
            'deficiency_number', 'site_name', 'resource', 'issue_description',
            'assignee_name', 'assignee_group_name', 'status', 'severity',
            'type', 'deficiency_type', 'category_name', 'raised_by_name',
            'raised_date', 'due_date', 'is_restricted', 'is_safety',
            'affects_qualification', 'actiontaken', 'parsed_actions'
        ]

    def get_parsed_actions(self, obj):
        """Return parsed actiontaken as list of dicts"""
        return obj.parsed_actions


class DeficiencyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for deficiency lists"""
    class Meta:
        model = Deficiency
        fields = [
            'deficiency_number', 'site_name', 'resource', 'issue_description',
            'status', 'severity', 'raised_by_name', 'raised_date', 'due_date'
        ]


class JourneyLogSerializer(serializers.ModelSerializer):
    """Serializer for JourneyLog model"""
    class Meta:
        model = JourneyLog
        fields = [
            'id', 'customer_name', 'log_date', 'site', 'resource_type',
            'resource', 'session_type', 'training_type', 'report_by',
            'created_at', 'updated_at'
        ]

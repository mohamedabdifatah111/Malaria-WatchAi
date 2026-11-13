from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import EvidenceSerializerMixin

from .models import PrevalenceEstimate


class PrevalenceEstimateSerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = PrevalenceEstimate
        fields = [
            "country", "region_id", "region_name", "year", "indicator", "estimate",
            "lower_interval", "upper_interval", "source_type", "model_version",
            "evidence_ids", "status",
        ]

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        return "available"


class PrevalenceUncertaintySerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    interval_width = serializers.SerializerMethodField()

    class Meta:
        model = PrevalenceEstimate
        fields = [
            "region_id", "year", "estimate", "lower_interval", "upper_interval",
            "interval_width", "nearest_survey_distance_km", "survey_density",
            "extrapolation_flag", "reliability_status", "evidence_ids",
        ]

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_interval_width(self, obj):
        return obj.interval_width
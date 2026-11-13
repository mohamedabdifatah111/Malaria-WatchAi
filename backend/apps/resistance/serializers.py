from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import EvidenceSerializerMixin

from .models import MarkerTrend, ResistanceObservation


class ResistanceObservationSerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    marker = serializers.CharField(source="marker.name", read_only=True)
    frequency = serializers.SerializerMethodField()
    confidence_interval_lower = serializers.SerializerMethodField()
    confidence_interval_upper = serializers.SerializerMethodField()

    class Meta:
        model = ResistanceObservation
        fields = [
            "country", "region_id", "marker", "year", "n_tested", "n_mutant", "frequency",
            "confidence_interval_lower", "confidence_interval_upper", "source_id", "evidence_ids",
        ]

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_frequency(self, obj):
        return obj.frequency

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_confidence_interval_lower(self, obj):
        return obj.confidence_interval()[0]

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_confidence_interval_upper(self, obj):
        return obj.confidence_interval()[1]


class MarkerTrendSerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    marker = serializers.CharField(source="marker.name", read_only=True)

    class Meta:
        model = MarkerTrend
        fields = [
            "country", "region_id", "marker", "year", "observed_frequency",
            "predicted_frequency", "n_tested", "confidence_interval_lower",
            "confidence_interval_upper", "validation_method", "model_version",
            "source_id", "evidence_ids",
        ]
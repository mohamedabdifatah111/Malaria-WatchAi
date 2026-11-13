from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import EvidenceSerializerMixin

from .models import DrugEfficacyRecord


class DrugEfficacySerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    study_id = serializers.SerializerMethodField()
    year_range = serializers.SerializerMethodField()

    class Meta:
        model = DrugEfficacyRecord
        fields = [
            "record_type", "study_id", "country", "region_id", "site", "drug",
            "followup_days", "n_patients", "acpr_percent", "failure_percent",
            "confidence_interval_lower", "confidence_interval_upper",
            "prediction_interval_lower", "prediction_interval_upper",
            "heterogeneity_i2", "study_count", "year_range", "source_id", "evidence_ids",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_study_id(self, obj):
        return obj.study_id or None

    @extend_schema_field(serializers.CharField())
    def get_year_range(self, obj):
        return obj.year_range
from rest_framework import serializers

from apps.core.serializers import EvidenceSerializerMixin

from .models import PopulationAtRisk


class PopulationAtRiskSerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PopulationAtRisk
        fields = [
            "country", "region_id", "year", "risk_class", "population",
            "population_source", "prevalence_model_version", "uncertainty_status",
            "evidence_ids",
        ]
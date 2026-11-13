from rest_framework import serializers

from apps.core.serializers import EvidenceSerializerMixin

from .models import SpeciesRecord


class SpeciesRecordSerializer(EvidenceSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SpeciesRecord
        fields = [
            "country", "region_id", "species", "record_type", "positive", "examined",
            "year", "source_id", "evidence_ids",
        ]
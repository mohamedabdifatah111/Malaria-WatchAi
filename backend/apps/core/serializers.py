from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class EvidenceSerializerMixin(serializers.Serializer):
    """Shared output fields. Each serializer lists the ones it needs in Meta.fields."""

    country = serializers.CharField(source="country.code", read_only=True)
    region_id = serializers.IntegerField(read_only=True)
    source_id = serializers.CharField(source="source.evidence_id", read_only=True)
    evidence_ids = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_evidence_ids(self, obj):
        return [obj.source.evidence_id]
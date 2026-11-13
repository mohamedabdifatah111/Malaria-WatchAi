from rest_framework import serializers

from .geojson import to_geojson_geometry
from .models import Country, Region


def _wants_boundary(context, default):
    request = context.get("request")
    value = request.query_params.get("include_boundary") if request else None
    if value is None:
        return default
    if value.lower() not in ("true", "false"):
        raise serializers.ValidationError({"include_boundary": "Use true or false."})
    return value.lower() == "true"


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["code", "name"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if _wants_boundary(self.context, default=False):
            data["boundary"] = to_geojson_geometry(instance.boundary)
        return data


class RegionSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True)
    parent_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Region
        fields = ["id", "name", "country_code", "admin_level", "parent_id", "external_id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if _wants_boundary(self.context, default=True):
            data["boundary"] = to_geojson_geometry(instance.boundary)
        return data
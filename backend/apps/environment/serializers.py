import math
from datetime import date, datetime, timezone

from rest_framework import serializers

from apps.geography.models import Country

from .bounds import inside_supported_area

COUNTRY_CODES = [code for code, _ in Country.CODE_CHOICES]
MAX_HISTORY_DAYS = 366
EARLIEST_DATE = date(1940, 1, 1)


class LocationQuerySerializer(serializers.Serializer):
    country = serializers.ChoiceField(choices=COUNTRY_CODES, required=False)
    region_id = serializers.IntegerField(required=False, min_value=1, max_value=2147483647)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")

        if "region_id" in attrs:
            if latitude is not None or longitude is not None:
                raise serializers.ValidationError(
                    "Provide either region_id or latitude and longitude, not both."
                )
            return attrs

        if latitude is None or longitude is None:
            raise serializers.ValidationError(
                "Provide both latitude and longitude (or region_id)."
            )
        if not (math.isfinite(latitude) and math.isfinite(longitude)):
            raise serializers.ValidationError("Coordinates must be finite numbers.")
        if not inside_supported_area(latitude, longitude, attrs.get("country")):
            raise serializers.ValidationError(
                "Coordinates are outside the supported area for Kenya, Tanzania and Ethiopia."
            )
        # About 1 km. Keeps cache keys bounded and avoids needless precision.
        attrs["latitude"] = round(latitude, 2)
        attrs["longitude"] = round(longitude, 2)
        return attrs


class HistoryQuerySerializer(LocationQuerySerializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start, end = attrs["start_date"], attrs["end_date"]
        today = datetime.now(timezone.utc).date()
        if start > end:
            raise serializers.ValidationError("start_date must not be after end_date.")
        if start < EARLIEST_DATE:
            raise serializers.ValidationError(f"start_date must be on or after {EARLIEST_DATE}.")
        if end > today:
            raise serializers.ValidationError("end_date cannot be in the future.")
        if (end - start).days + 1 > MAX_HISTORY_DAYS:
            raise serializers.ValidationError(
                f"The date range cannot exceed {MAX_HISTORY_DAYS} days."
            )
        return attrs
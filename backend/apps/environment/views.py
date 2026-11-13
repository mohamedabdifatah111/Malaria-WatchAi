from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.errors import NotAvailableYet, ProviderUnavailable
from apps.evidence.models import EvidenceSource
from apps.geography.models import Region

from . import services
from .provider import PROVIDER_NAME, ProviderError
from .serializers import HistoryQuerySerializer, LocationQuerySerializer


def _evidence_ids():
    return sorted(
        EvidenceSource.objects.filter(
            provider=PROVIDER_NAME, evidence_type=EvidenceSource.EvidenceType.WEATHER
        ).values_list("evidence_id", flat=True)
    )


def _location(data):
    """Return (latitude, longitude, country_code, region_id) from coordinates or a region."""
    if "region_id" not in data:
        return data["latitude"], data["longitude"], data.get("country"), None

    region = Region.objects.select_related("country").filter(pk=data["region_id"]).first()
    if region is None:
        raise NotFound()
    if data.get("country") and region.country.code != data["country"]:
        raise ValidationError({"country": "Does not match the region's country."})
    if region.boundary is None:
        raise NotAvailableYet("This region has no boundary geometry loaded yet.")
    # A point guaranteed to lie inside the region (a centroid can fall outside concave shapes).
    point = region.boundary.point_on_surface
    return round(point.y, 2), round(point.x, 2), region.country.code, region.id


class _WeatherView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "weather"


class CurrentWeatherView(_WeatherView):
    """Current model-based weather for a coordinate or region. Not malaria prevalence."""

    @extend_schema(
        parameters=[LocationQuerySerializer],
        responses={200: OpenApiTypes.OBJECT},
        tags=["environment"],
    )
    def get(self, request):
        query = LocationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        latitude, longitude, country, region_id = _location(query.validated_data)

        try:
            payload = services.get_current(latitude, longitude)
        except ProviderError:
            raise ProviderUnavailable()

        return Response(
            {
                "status": "available",
                "country": country,
                "region_id": region_id,
                "latitude": latitude,
                "longitude": longitude,
                "data_type": "current",
                **payload,
                "evidence_ids": _evidence_ids(),
                "notes": [
                    "Model-based current conditions from the provider, not a station observation.",
                    "Current weather is not current malaria prevalence or risk.",
                    "Weather is an additional monitoring feature, not a substitute for the "
                    "historical covariates used in the prevalence model.",
                ],
            }
        )


class WeatherHistoryView(_WeatherView):
    """Historical weather (reanalysis) for a coordinate or region and a date range."""

    @extend_schema(
        parameters=[HistoryQuerySerializer],
        responses={200: OpenApiTypes.OBJECT},
        tags=["environment"],
    )
    def get(self, request):
        query = HistoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        latitude, longitude, country, region_id = _location(data)

        try:
            payload = services.get_history(latitude, longitude, data["start_date"], data["end_date"])
        except ProviderError:
            raise ProviderUnavailable()

        return Response(
            {
                "status": "available",
                "country": country,
                "region_id": region_id,
                "latitude": latitude,
                "longitude": longitude,
                "start_date": data["start_date"].isoformat(),
                "end_date": data["end_date"].isoformat(),
                "data_type": payload["data_type"],
                "provider": payload["provider"],
                "retrieved_at": payload["retrieved_at"],
                "evidence_ids": _evidence_ids(),
                "notes": [
                    "Historical values are reanalysis-based, not direct station observations.",
                    "relative_humidity_percent is the arithmetic mean of 24 hourly provider "
                    "values and is null when any hour is missing.",
                    "Null values mean the provider returned no value for that day.",
                ],
                "records": payload["records"],
            }
        )
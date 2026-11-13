from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.geography.geojson import to_geojson_geometry

from .filters import PrevalenceFilter, PrevalenceMapFilter
from .models import PrevalenceEstimate
from .serializers import PrevalenceEstimateSerializer, PrevalenceUncertaintySerializer

_QUERYSET = PrevalenceEstimate.objects.select_related("country", "region", "source")
MAX_MAP_FEATURES = 500


class PrevalenceListView(generics.ListAPIView):
    """Prevalence estimates. Filters: country, region_id, year, source_type."""

    queryset = _QUERYSET
    serializer_class = PrevalenceEstimateSerializer
    filterset_class = PrevalenceFilter


class PrevalenceUncertaintyView(generics.ListAPIView):
    """Uncertainty fields stored with each estimate. Null means not supplied by the model."""

    queryset = _QUERYSET
    serializer_class = PrevalenceUncertaintySerializer
    filterset_class = PrevalenceFilter


class PrevalenceMapView(generics.GenericAPIView):
    """GeoJSON FeatureCollection (RFC 7946, EPSG:4326) of estimates for regions that have boundaries.

    resolution is the administrative level (ADM1 or ADM2). Grid-cell maps are not offered yet.
    """

    queryset = PrevalenceEstimate.objects.filter(region__boundary__isnull=False).select_related(
        "country", "region", "source"
    )
    filterset_class = PrevalenceMapFilter
    pagination_class = None
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "map"

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["prevalence"])
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        rows = list(queryset[:MAX_MAP_FEATURES])
        features = [
            {
                "type": "Feature",
                "id": row.id,
                "geometry": to_geojson_geometry(row.region.boundary),
                "properties": {
                    "feature_id": str(row.id),
                    "region_id": row.region_id,
                    "region_name": row.region.name,
                    "country": row.country.code,
                    "year": row.year,
                    "indicator": row.indicator,
                    "estimate": row.estimate,
                    "lower_interval": row.lower_interval,
                    "upper_interval": row.upper_interval,
                    "source_type": row.source_type,
                    "model_version": row.model_version or None,
                    "evidence_ids": [row.source.evidence_id],
                },
            }
            for row in rows
        ]
        return Response(
            {
                "type": "FeatureCollection",
                "features": features,
                "feature_count": len(features),
                "total_matching": total,
                "truncated": total > len(features),
                "data_status": "available" if features else "no_data",
            }
        )
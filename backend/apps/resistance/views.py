from rest_framework import generics

from .filters import ResistanceFilter, TrendFilter
from .models import MarkerTrend, ResistanceObservation
from .serializers import MarkerTrendSerializer, ResistanceObservationSerializer


class ResistanceListView(generics.ListAPIView):
    """Marker counts with computed frequency (Wilson 95% interval). Not treatment failure."""

    queryset = ResistanceObservation.objects.select_related("country", "region", "marker", "source")
    serializer_class = ResistanceObservationSerializer
    filterset_class = ResistanceFilter


class ResistanceTrendListView(generics.ListAPIView):
    """Observed and predicted marker frequencies. Not equivalent to clinical treatment failure."""

    queryset = MarkerTrend.objects.select_related("country", "region", "marker", "source")
    serializer_class = MarkerTrendSerializer
    filterset_class = TrendFilter
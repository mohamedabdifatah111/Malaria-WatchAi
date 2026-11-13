from rest_framework import generics

from .filters import SpeciesFilter
from .models import SpeciesRecord
from .serializers import SpeciesRecordSerializer


class SpeciesListView(generics.ListAPIView):
    """Species evidence. record_type distinguishes survey, presence_only and modelled records."""

    queryset = SpeciesRecord.objects.select_related("country", "region", "source")
    serializer_class = SpeciesRecordSerializer
    filterset_class = SpeciesFilter
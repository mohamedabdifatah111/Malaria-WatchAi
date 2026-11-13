from rest_framework import generics

from .filters import PopulationFilter
from .models import PopulationAtRisk
from .serializers import PopulationAtRiskSerializer


class PopulationAtRiskListView(generics.ListAPIView):
    """People living in each PfPR risk class. Not infected-population counts."""

    queryset = PopulationAtRisk.objects.select_related("country", "region", "source")
    serializer_class = PopulationAtRiskSerializer
    filterset_class = PopulationFilter
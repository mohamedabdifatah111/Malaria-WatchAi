from rest_framework import generics

from .filters import EfficacyFilter
from .models import DrugEfficacyRecord
from .serializers import DrugEfficacySerializer


class DrugEfficacyListView(generics.ListAPIView):
    """Efficacy records. record_type is 'study' or 'pooled'; follow-up periods are never merged."""

    queryset = DrugEfficacyRecord.objects.select_related("country", "region", "source")
    serializer_class = DrugEfficacySerializer
    filterset_class = EfficacyFilter
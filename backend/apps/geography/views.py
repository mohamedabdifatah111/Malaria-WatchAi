from rest_framework import generics

from apps.core.pagination import StandardPagination

from .filters import RegionFilter
from .models import Country, Region
from .serializers import CountrySerializer, RegionSerializer


class RegionPagination(StandardPagination):
    max_page_size = 50  # boundaries can be large payloads


class CountryListView(generics.ListAPIView):
    """Supported countries. Add include_boundary=true for the country boundary."""

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    pagination_class = None
    filter_backends = []


class RegionListView(generics.ListAPIView):
    """Administrative regions. Filters: country, level, search. Add include_boundary=false to omit geometry."""

    queryset = Region.objects.select_related("country")
    serializer_class = RegionSerializer
    filterset_class = RegionFilter
    pagination_class = RegionPagination


class RegionDetailView(generics.RetrieveAPIView):
    queryset = Region.objects.select_related("country")
    serializer_class = RegionSerializer
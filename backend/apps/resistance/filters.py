import django_filters
from rest_framework import serializers

from apps.core.filters import country_filter, region_id_filter, year_filter

from .models import Marker, MarkerTrend, ResistanceObservation


class _MarkerFilterMixin(django_filters.FilterSet):
    country = country_filter()
    region_id = region_id_filter()
    year = year_filter()
    marker = django_filters.CharFilter(method="filter_marker", max_length=50)

    def filter_marker(self, queryset, name, value):
        marker = Marker.objects.filter(name__iexact=value).first()
        if marker is None:
            raise serializers.ValidationError({"marker": "Unsupported marker."})
        return queryset.filter(marker=marker)


class ResistanceFilter(_MarkerFilterMixin):
    class Meta:
        model = ResistanceObservation
        fields = []


class TrendFilter(_MarkerFilterMixin):
    class Meta:
        model = MarkerTrend
        fields = []
import django_filters
from rest_framework import serializers

from apps.core.filters import country_filter, region_id_filter, year_filter

from .models import SpeciesRecord


def normalise_species(value):
    """Accept 'Plasmodium vivax' or 'P. vivax' (any case); return the stored name or None."""
    text = " ".join(value.lower().split())
    if text.startswith("plasmodium "):
        text = "p. " + text[len("plasmodium "):]
    for stored in SpeciesRecord.Species.values:
        if stored.lower() == text:
            return stored
    return None


class SpeciesFilter(django_filters.FilterSet):
    country = country_filter()
    region_id = region_id_filter()
    year = year_filter()
    species = django_filters.CharFilter(method="filter_species", max_length=50)

    class Meta:
        model = SpeciesRecord
        fields = []

    def filter_species(self, queryset, name, value):
        canonical = normalise_species(value)
        if canonical is None:
            raise serializers.ValidationError({"species": "Unsupported species."})
        return queryset.filter(species=canonical)
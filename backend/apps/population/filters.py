import django_filters

from apps.core.filters import country_filter, region_id_filter, year_filter

from .models import PopulationAtRisk


class PopulationFilter(django_filters.FilterSet):
    country = country_filter()
    region_id = region_id_filter()
    year = year_filter()

    class Meta:
        model = PopulationAtRisk
        fields = []
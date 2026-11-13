import django_filters
from django.core.validators import RegexValidator

from apps.core.filters import country_filter, region_id_filter, year_filter
from apps.geography.models import AdminLevel

from .models import PrevalenceEstimate


class PrevalenceFilter(django_filters.FilterSet):
    country = country_filter()
    region_id = region_id_filter()
    year = year_filter()
    source_type = django_filters.ChoiceFilter(choices=PrevalenceEstimate.SourceType.choices)

    class Meta:
        model = PrevalenceEstimate
        fields = []


class PrevalenceMapFilter(django_filters.FilterSet):
    country = country_filter()
    year = year_filter()
    resolution = django_filters.ChoiceFilter(
        field_name="region__admin_level", choices=AdminLevel.choices
    )
    indicator = django_filters.CharFilter(
        field_name="indicator",
        lookup_expr="iexact",
        max_length=20,
        validators=[RegexValidator(r"^[A-Za-z0-9_]{1,20}$", "Invalid indicator.")],
    )
    source_type = django_filters.ChoiceFilter(choices=PrevalenceEstimate.SourceType.choices)

    class Meta:
        model = PrevalenceEstimate
        fields = []
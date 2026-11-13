import django_filters

from .models import AdminLevel, Country, Region


class RegionFilter(django_filters.FilterSet):
    country = django_filters.ChoiceFilter(
        field_name="country__code",
        choices=[(code, code) for code, _ in Country.CODE_CHOICES],
    )
    level = django_filters.ChoiceFilter(
        field_name="admin_level", choices=AdminLevel.choices
    )
    search = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains", max_length=100
    )

    class Meta:
        model = Region
        fields = []
import django_filters
from django.core.validators import RegexValidator

from apps.core.filters import IntegerFilter, country_filter, region_id_filter

from .models import DrugEfficacyRecord


class EfficacyFilter(django_filters.FilterSet):
    country = country_filter()
    region_id = region_id_filter()
    drug = django_filters.CharFilter(
        field_name="drug",
        lookup_expr="iexact",
        max_length=20,
        validators=[RegexValidator(r"^[A-Za-z0-9+\-]{1,20}$", "Invalid drug code.")],
    )
    followup_days = IntegerFilter(field_name="followup_days", min_value=1, max_value=365)
    record_type = django_filters.ChoiceFilter(choices=DrugEfficacyRecord.RecordType.choices)

    class Meta:
        model = DrugEfficacyRecord
        fields = []
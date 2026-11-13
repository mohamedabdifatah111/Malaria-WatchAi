import django_filters
from django import forms

from apps.geography.models import Country

COUNTRY_CHOICES = [(code, code) for code, _ in Country.CODE_CHOICES]


class IntegerFilter(django_filters.NumberFilter):
    """Strict integers only, so 2020.5 is rejected instead of silently truncated."""

    field_class = forms.IntegerField


def country_filter():
    return django_filters.ChoiceFilter(field_name="country__code", choices=COUNTRY_CHOICES)


def year_filter(field_name="year"):
    return IntegerFilter(field_name=field_name, min_value=1900, max_value=2100)


def region_id_filter():
    return IntegerFilter(field_name="region_id", min_value=1, max_value=2147483647)
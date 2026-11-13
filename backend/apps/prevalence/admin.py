from django.contrib import admin

from .models import PrevalenceEstimate, PrevalenceObservation


@admin.register(PrevalenceObservation)
class PrevalenceObservationAdmin(admin.ModelAdmin):
    list_display = ("survey_id", "country", "survey_year", "n_examined", "n_positive", "source")
    list_filter = ("country", "survey_year")


@admin.register(PrevalenceEstimate)
class PrevalenceEstimateAdmin(admin.ModelAdmin):
    list_display = ("region", "year", "indicator", "estimate", "source_type", "model_version")
    list_filter = ("country", "source_type", "year")
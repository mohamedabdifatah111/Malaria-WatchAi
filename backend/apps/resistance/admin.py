from django.contrib import admin

from .models import Marker, MarkerTrend, ResistanceObservation


@admin.register(Marker)
class MarkerAdmin(admin.ModelAdmin):
    list_display = ("name", "gene")


@admin.register(ResistanceObservation)
class ResistanceObservationAdmin(admin.ModelAdmin):
    list_display = ("marker", "country", "region", "year", "n_tested", "n_mutant")
    list_filter = ("country", "marker", "year")


@admin.register(MarkerTrend)
class MarkerTrendAdmin(admin.ModelAdmin):
    list_display = ("marker", "country", "region", "year", "observed_frequency", "predicted_frequency")
    list_filter = ("country", "marker")
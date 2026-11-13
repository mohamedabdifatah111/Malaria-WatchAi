from django.contrib import admin

from .models import PopulationAtRisk


@admin.register(PopulationAtRisk)
class PopulationAtRiskAdmin(admin.ModelAdmin):
    list_display = ("region", "year", "risk_class", "population", "prevalence_model_version")
    list_filter = ("country", "year", "risk_class")
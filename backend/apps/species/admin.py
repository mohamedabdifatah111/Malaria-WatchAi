from django.contrib import admin

from .models import SpeciesRecord


@admin.register(SpeciesRecord)
class SpeciesRecordAdmin(admin.ModelAdmin):
    list_display = ("species", "record_type", "country", "region", "year", "positive", "examined")
    list_filter = ("country", "species", "record_type")
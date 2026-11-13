from django.contrib import admin

from .models import Country, Region


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    exclude = ("boundary",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "admin_level", "external_id")
    list_filter = ("country", "admin_level")
    search_fields = ("name", "external_id")
    exclude = ("boundary",)
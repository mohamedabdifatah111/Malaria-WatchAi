from django.contrib import admin

from .models import EvidenceSource


@admin.register(EvidenceSource)
class EvidenceSourceAdmin(admin.ModelAdmin):
    list_display = ("evidence_id", "source_name", "provider", "evidence_type", "country_code")
    list_filter = ("evidence_type", "country_code")
    search_fields = ("evidence_id", "source_name", "provider")
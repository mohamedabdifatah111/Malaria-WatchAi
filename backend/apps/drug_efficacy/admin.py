from django.contrib import admin

from .models import DrugEfficacyRecord


@admin.register(DrugEfficacyRecord)
class DrugEfficacyRecordAdmin(admin.ModelAdmin):
    list_display = ("record_type", "study_id", "country", "drug", "followup_days", "n_patients", "acpr_percent")
    list_filter = ("record_type", "country", "drug", "followup_days")
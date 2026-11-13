from django.contrib import admin

from .models import AssistantBrief, AssistantRun, BriefReviewEvent, ToolCallLog


class ReadOnlyAdmin(admin.ModelAdmin):
    """Audit records are viewable but never editable through the admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AssistantRun)
class AssistantRunAdmin(ReadOnlyAdmin):
    list_display = ("run_id", "guardrail_decision", "country", "created_at")


@admin.register(ToolCallLog)
class ToolCallLogAdmin(ReadOnlyAdmin):
    list_display = ("request_id", "tool_name", "status", "duration_ms", "created_at")


@admin.register(AssistantBrief)
class AssistantBriefAdmin(ReadOnlyAdmin):
    list_display = ("brief_id", "status", "country", "created_at")


@admin.register(BriefReviewEvent)
class BriefReviewEventAdmin(ReadOnlyAdmin):
    list_display = ("brief", "decision", "reviewer", "created_at")
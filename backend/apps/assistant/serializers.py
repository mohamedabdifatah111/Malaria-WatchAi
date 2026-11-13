import json

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.geography.models import Country

from .models import AssistantBrief, AssistantRun, ToolCallLog

MAX_EDITED_CHARS = 20000


class BriefRequestSerializer(serializers.Serializer):
    country = serializers.ChoiceField(choices=[code for code, _ in Country.CODE_CHOICES])
    region_id = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=2147483647)
    question = serializers.CharField(min_length=3, max_length=500)


class ReviewRequestSerializer(serializers.Serializer):
    brief_id = serializers.UUIDField()
    decision = serializers.ChoiceField(choices=["approve", "edit", "reject"])
    reviewer = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=100,
        help_text="Ignored. The reviewer is always the authenticated user.",
    )
    edited_content = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        content = attrs.get("edited_content")
        if attrs["decision"] == "edit":
            if not content:
                raise serializers.ValidationError({"edited_content": "Required when decision is edit."})
            if len(json.dumps(content)) > MAX_EDITED_CHARS:
                raise serializers.ValidationError({"edited_content": "Edited content is too large."})
        elif content is not None:
            raise serializers.ValidationError({"edited_content": "Only allowed when decision is edit."})
        attrs.pop("reviewer", None)
        return attrs


class BriefSerializer(serializers.ModelSerializer):
    region_id = serializers.IntegerField(read_only=True)
    tool_trace_id = serializers.UUIDField(source="run.run_id", read_only=True)
    review = serializers.SerializerMethodField()

    class Meta:
        model = AssistantBrief
        fields = [
            "brief_id", "status", "country", "region_id", "summary", "findings",
            "evidence_ids", "uncertainties", "limitations", "tool_trace_id",
            "created_at", "edited_content", "review",
        ]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_review(self, obj):
        event = obj.review_events.select_related("reviewer").first()
        if event is None:
            return None
        return {
            "decision": event.decision,
            "reviewed_at": event.created_at.isoformat(),
            "reviewer": event.reviewer.get_username() if event.reviewer else None,
        }


class ToolCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCallLog
        fields = ["request_id", "tool_name", "arguments", "result", "evidence_ids", "status", "duration_ms", "created_at"]


class AssistantRunLogSerializer(serializers.ModelSerializer):
    tool_calls = ToolCallLogSerializer(many=True, read_only=True)
    evidence_ids = serializers.SerializerMethodField()
    reviewer_decision = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = AssistantRun
        fields = [
            "run_id", "question", "guardrail_decision", "guardrail_reason", "tool_calls",
            "evidence_ids", "draft_output", "grounding_result", "reviewer_decision", "timestamp",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_evidence_ids(self, obj):
        found = set()
        for call in obj.tool_calls.all():
            found.update(call.evidence_ids)
        return sorted(found)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_reviewer_decision(self, obj):
        brief = getattr(obj, "brief", None)
        if brief is None:
            return None
        events = list(brief.review_events.all())
        return events[0].decision if events else None
import uuid

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.core.models import TimeStampedModel
from apps.geography.models import Region


def _json(**kwargs):
    return models.JSONField(encoder=DjangoJSONEncoder, **kwargs)


class AssistantRun(models.Model):
    """One assistant request. The question is untrusted text and is never executed."""

    class Guardrail(models.TextChoices):
        ALLOWED = "allowed", "Allowed"
        REFUSED = "refused", "Refused"

    run_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    question = models.TextField()
    guardrail_decision = models.CharField(max_length=10, choices=Guardrail.choices)
    guardrail_reason = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=3, blank=True)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    draft_output = _json(null=True, blank=True)
    grounding_result = _json(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return str(self.run_id)


class ToolCallLog(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    run = models.ForeignKey(AssistantRun, on_delete=models.PROTECT, related_name="tool_calls")
    tool_name = models.CharField(max_length=50)
    arguments = _json(default=dict)
    result = _json(default=dict)
    evidence_ids = _json(default=list)
    status = models.CharField(max_length=20)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.tool_name} ({self.status})"


class AssistantBrief(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        EDITED = "edited", "Edited (awaiting approval)"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    brief_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    run = models.OneToOneField(AssistantRun, on_delete=models.PROTECT, related_name="brief")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    country = models.CharField(max_length=3)
    region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    summary = models.TextField()
    findings = _json(default=list)
    evidence_ids = _json(default=list)
    uncertainties = _json(default=list)
    limitations = _json(default=list)
    original_draft = _json(default=dict)  # frozen at creation, never modified
    edited_content = _json(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.brief_id} ({self.status})"


class BriefReviewEvent(models.Model):
    """Append-only review history."""

    brief = models.ForeignKey(AssistantBrief, on_delete=models.PROTECT, related_name="review_events")
    decision = models.CharField(max_length=10)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    edited_content = _json(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
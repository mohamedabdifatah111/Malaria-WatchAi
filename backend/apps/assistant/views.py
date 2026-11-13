from django.db import transaction
from django.utils import timezone  # noqa: F401  (kept for future review timestamps)
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsReviewer
from apps.core.errors import Conflict
from apps.geography.models import Country, Region

from .models import AssistantBrief, AssistantRun, BriefReviewEvent
from .serializers import (
    AssistantRunLogSerializer,
    BriefRequestSerializer,
    BriefSerializer,
    ReviewRequestSerializer,
)
from .services.brief_builder import build_brief

_DECISION_STATUS = {
    "approve": AssistantBrief.Status.APPROVED,
    "edit": AssistantBrief.Status.EDITED,
    "reject": AssistantBrief.Status.REJECTED,
}
_FINAL = (AssistantBrief.Status.APPROVED, AssistantBrief.Status.REJECTED)


class BriefCreateView(APIView):
    """Generate a draft brief from stored evidence. Public for the demo, rate limited."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "brief"

    @extend_schema(request=BriefRequestSerializer, responses={201: BriefSerializer}, tags=["assistant"])
    def post(self, request):
        serializer = BriefRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        country = Country.objects.filter(code=data["country"]).first()
        if country is None:
            raise NotFound()
        region = None
        if data.get("region_id"):
            region = Region.objects.select_related("country").filter(
                pk=data["region_id"], country=country
            ).first()
            if region is None:
                raise NotFound()

        brief = build_brief(country=country, region=region, question=data["question"])
        return Response(BriefSerializer(brief).data, status=201)


class BriefReviewView(APIView):
    """Approve, edit or reject a draft. Reviewer identity comes from the token only."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsReviewer]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "review"

    @extend_schema(request=ReviewRequestSerializer, responses={200: BriefSerializer}, tags=["assistant"])
    def post(self, request):
        serializer = ReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            brief = (
                AssistantBrief.objects.select_for_update(of=("self",))
                .filter(brief_id=data["brief_id"])
                .first()
            )
            if brief is None:
                raise NotFound()
            if brief.status in _FINAL:
                raise Conflict("This brief has already been reviewed.")

            BriefReviewEvent.objects.create(
                brief=brief,
                decision=data["decision"],
                reviewer=request.user,
                edited_content=data.get("edited_content"),
            )
            if data["decision"] == "edit":
                brief.edited_content = data["edited_content"]
            brief.status = _DECISION_STATUS[data["decision"]]
            brief.save(update_fields=["status", "edited_content", "updated_at"])

        return Response(BriefSerializer(brief).data)


class AssistantLogListView(generics.ListAPIView):
    """Audit trail of assistant runs and tool calls. Reviewers only."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsReviewer]
    filter_backends = []
    serializer_class = AssistantRunLogSerializer
    queryset = (
        AssistantRun.objects.select_related("brief")
        .prefetch_related("tool_calls", "brief__review_events")
    )
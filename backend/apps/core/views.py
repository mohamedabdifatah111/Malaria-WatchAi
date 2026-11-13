import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .responses import error_body

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Public liveness and database connectivity check. Exposes no internals."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["system"])
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            logger.error("Health check: database unavailable", exc_info=True)
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE", "The service is temporarily unavailable."
                ),
                status=503,
            )
        return Response({"status": "ok", "database": "ok"})


def not_found(request, exception=None):
    return JsonResponse(
        error_body("RESOURCE_NOT_FOUND", "The requested resource was not found."),
        status=404,
    )


def server_error(request):
    return JsonResponse(
        error_body("INTERNAL_SERVER_ERROR", "An internal error occurred."),
        status=500,
    )
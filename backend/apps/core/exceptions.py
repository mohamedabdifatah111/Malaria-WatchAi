import logging

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .responses import error_body

logger = logging.getLogger(__name__)

_ERRORS = {
    400: ("INVALID_REQUEST", "The request is invalid."),
    401: ("AUTHENTICATION_REQUIRED", "Authentication is required for this request."),
    403: ("PERMISSION_DENIED", "You do not have permission to perform this action."),
    404: ("RESOURCE_NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "This method is not allowed for this endpoint."),
    409: ("CONFLICT", "The request conflicts with the current state of the resource."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "The request content type is not supported."),
    422: ("UNPROCESSABLE_ENTITY", "The request could not be processed."),
    429: ("RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later."),
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Full trace goes to server logs only, never to the client.
        logger.error("Unhandled API exception", exc_info=exc)
        return Response(
            error_body("INTERNAL_SERVER_ERROR", "An internal error occurred."),
            status=500,
        )

    code, message = _ERRORS.get(
        response.status_code, ("ERROR", "The request could not be completed.")
    )
    api_code = getattr(exc, "api_code", None)
    if api_code:
        code, message = api_code, str(exc.detail)

    body = error_body(code, message)
    if isinstance(exc, ValidationError):
        body["error"]["details"] = response.data
    extra = getattr(exc, "extra", None)
    if extra:
        body["error"]["details"] = extra
    response.data = body
    return response
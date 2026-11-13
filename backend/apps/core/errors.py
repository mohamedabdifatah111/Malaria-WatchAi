from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"
    api_code = "CONFLICT"


class GuardrailRefusal(APIException):
    status_code = 422
    default_detail = (
        "This assistant cannot provide individual diagnosis, medication dosing "
        "or treatment advice, or process this kind of request."
    )
    default_code = "guardrail_refusal"
    api_code = "GUARDRAIL_REFUSAL"

    def __init__(self, detail=None, run_id=None):
        super().__init__(detail)
        self.extra = {"run_id": str(run_id)} if run_id else None
        

class NotAvailableYet(APIException):
    status_code = 501
    default_detail = "This feature is not available yet."
    default_code = "not_available"
    api_code = "NOT_AVAILABLE"


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = "The weather provider is temporarily unavailable."
    default_code = "provider_unavailable"
    api_code = "PROVIDER_UNAVAILABLE"
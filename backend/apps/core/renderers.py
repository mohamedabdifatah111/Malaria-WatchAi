from rest_framework.renderers import JSONRenderer

from .responses import build_meta


class EnvelopeJSONRenderer(JSONRenderer):
    """Wrap successful responses in {"success": true, "data": ..., "meta": ...}.

    Error bodies (status >= 400) and bodies that are already enveloped
    (for example paginated responses) are passed through unchanged.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        status_code = getattr(response, "status_code", 200)

        if status_code == 204:
            return b""

        already_wrapped = (
            isinstance(data, dict) and data.get("success") is True and "meta" in data
        )
        if status_code >= 400 or already_wrapped:
            return super().render(data, accepted_media_type, renderer_context)

        payload = {"success": True, "data": data, "meta": build_meta()}
        return super().render(payload, accepted_media_type, renderer_context)
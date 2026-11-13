from django.utils import timezone


def build_meta(extra=None):
    """Standard meta block from docs/API.md."""
    meta = {
        "timestamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "malaria-watchai",
    }
    if extra:
        meta.update(extra)
    return meta


def error_body(code, message):
    return {"success": False, "error": {"code": code, "message": message}}
from django.core.cache import cache

from . import provider

CURRENT_TTL_SECONDS = 600
HISTORY_TTL_SECONDS = 86400


def get_current(latitude, longitude):
    key = f"wx:current:{latitude:.2f}:{longitude:.2f}"
    payload = cache.get(key)
    if payload is None:
        payload = provider.get_current(latitude, longitude)  # failures are never cached
        cache.set(key, payload, CURRENT_TTL_SECONDS)
    return payload


def get_history(latitude, longitude, start_date, end_date):
    key = f"wx:history:{latitude:.2f}:{longitude:.2f}:{start_date}:{end_date}"
    payload = cache.get(key)
    if payload is None:
        payload = provider.get_history(latitude, longitude, start_date, end_date)
        cache.set(key, payload, HISTORY_TTL_SECONDS)
    return payload
import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PROVIDER_NAME = "Open-Meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 5_000_000

CURRENT_VARIABLES = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
DAILY_VARIABLES = (
    "temperature_2m_mean",
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
)


class ProviderError(Exception):
    """The weather provider failed or returned something unusable."""


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def fetch_json(url, params):
    """GET a fixed provider URL and return parsed JSON. Raises ProviderError on any failure."""
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "malaria-watchai/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Weather provider request failed: %s", type(exc).__name__)
        raise ProviderError("Provider request failed.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("Provider response too large.")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProviderError("Provider returned invalid JSON.") from exc
    if not isinstance(data, dict) or data.get("error"):
        raise ProviderError("Provider returned an error.")
    return data


def get_current(latitude, longitude):
    data = fetch_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": CURRENT_VARIABLES,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        },
    )
    current = data.get("current")
    if not isinstance(current, dict) or not isinstance(current.get("time"), str):
        raise ProviderError("Unexpected provider response shape.")
    try:
        observed = datetime.fromisoformat(current["time"])
    except ValueError as exc:
        raise ProviderError("Unexpected provider timestamp.") from exc
    # Timestamps are requested in GMT (the provider default).
    observed = (
        observed.astimezone(timezone.utc)
        if observed.tzinfo
        else observed.replace(tzinfo=timezone.utc)
    )
    return {
        "temperature_c": _number(current.get("temperature_2m")),
        "relative_humidity_percent": _number(current.get("relative_humidity_2m")),
        "precipitation_mm": _number(current.get("precipitation")),
        "wind_speed_kmh": _number(current.get("wind_speed_10m")),
        "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": PROVIDER_NAME,
        "retrieved_at": _now_iso(),
    }


def _daily_mean_humidity(hourly):
    """Mean of 24 hourly values per day; None when any hour is missing."""
    if not isinstance(hourly, dict):
        return {}
    times = hourly.get("time")
    values = hourly.get("relative_humidity_2m")
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        return {}
    by_day = {}
    for stamp, value in zip(times, values):
        if isinstance(stamp, str):
            by_day.setdefault(stamp[:10], []).append(_number(value))
    result = {}
    for day, readings in by_day.items():
        if len(readings) == 24 and all(r is not None for r in readings):
            result[day] = round(sum(readings) / 24, 2)
        else:
            result[day] = None
    return result


def get_history(latitude, longitude, start_date, end_date):
    data = fetch_json(
        ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ",".join(DAILY_VARIABLES),
            "hourly": "relative_humidity_2m",
        },
    )
    daily = data.get("daily")
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise ProviderError("Unexpected provider response shape.")
    days = daily["time"]
    series = {}
    for name in DAILY_VARIABLES:
        values = daily.get(name)
        if not isinstance(values, list) or len(values) != len(days):
            raise ProviderError("Provider response is missing a daily series.")
        series[name] = values

    humidity = _daily_mean_humidity(data.get("hourly"))
    records = []
    for index, day in enumerate(days):
        if not isinstance(day, str):
            raise ProviderError("Unexpected provider date.")
        records.append(
            {
                "date": day,
                "temperature_mean_c": _number(series["temperature_2m_mean"][index]),
                "temperature_min_c": _number(series["temperature_2m_min"][index]),
                "temperature_max_c": _number(series["temperature_2m_max"][index]),
                "precipitation_mm": _number(series["precipitation_sum"][index]),
                "relative_humidity_percent": humidity.get(day),
                "provider": PROVIDER_NAME,
                "data_type": "reanalysis",
            }
        )
    return {
        "provider": PROVIDER_NAME,
        "data_type": "reanalysis",
        "retrieved_at": _now_iso(),
        "records": records,
    }
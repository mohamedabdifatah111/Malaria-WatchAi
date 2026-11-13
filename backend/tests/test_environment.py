import pytest

from apps.environment import provider
from apps.evidence.models import EvidenceSource
from tests.factories import make_boundary, make_region

BASE = "/api/v1/environment"
LOCATION = "latitude=-1.2864&longitude=36.8172"

CURRENT_PAYLOAD = {
    "current": {
        "time": "2026-11-13T09:00",
        "interval": 900,
        "temperature_2m": 21.4,
        "relative_humidity_2m": 63,
        "precipitation": 0.0,
        "wind_speed_10m": 11.2,
    }
}


def archive_payload():
    day1, day2 = "2020-01-01", "2020-01-02"
    hours = [f"{day1}T{h:02d}:00" for h in range(24)] + [f"{day2}T{h:02d}:00" for h in range(24)]
    return {
        "daily": {
            "time": [day1, day2],
            "temperature_2m_mean": [19.5, 20.0],
            "temperature_2m_min": [14.0, 15.0],
            "temperature_2m_max": [26.0, 27.0],
            "precipitation_sum": [0.0, 3.2],
        },
        "hourly": {
            "time": hours,
            "relative_humidity_2m": [50.0] * 24 + [60.0] * 23 + [None],
        },
    }


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def blocked(url, params):
        raise AssertionError("A real network call was attempted in a test.")

    monkeypatch.setattr(provider, "fetch_json", blocked)


def use_payload(monkeypatch, payload, calls=None):
    def fake(url, params):
        if calls is not None:
            calls.append((url, params))
        return payload

    monkeypatch.setattr(provider, "fetch_json", fake)


def raise_provider_error(monkeypatch):
    def failing(url, params):
        raise provider.ProviderError("secret internal detail")

    monkeypatch.setattr(provider, "fetch_json", failing)


# ---------- current ----------

@pytest.mark.django_db
def test_current_success(client, monkeypatch):
    calls = []
    use_payload(monkeypatch, CURRENT_PAYLOAD, calls)
    response = client.get(f"{BASE}/current/?{LOCATION}")
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["status"] == "available"
    assert data["data_type"] == "current"
    assert data["latitude"] == -1.29 and data["longitude"] == 36.82
    assert data["temperature_c"] == 21.4
    assert data["relative_humidity_percent"] == 63.0
    assert data["precipitation_mm"] == 0.0
    assert data["wind_speed_kmh"] == 11.2
    assert data["observed_at"] == "2026-11-13T09:00:00Z"
    assert data["provider"] == "Open-Meteo"
    assert data["retrieved_at"].endswith("Z")
    assert data["evidence_ids"] == []
    assert any("not current malaria" in note for note in data["notes"])

    url, params = calls[0]
    assert url.startswith("https://api.open-meteo.com/")
    assert params["latitude"] == -1.29
    assert "temperature_2m" in params["current"]


@pytest.mark.django_db
def test_current_is_cached(client, monkeypatch):
    calls = []
    use_payload(monkeypatch, CURRENT_PAYLOAD, calls)
    client.get(f"{BASE}/current/?{LOCATION}")
    client.get(f"{BASE}/current/?{LOCATION}")
    assert len(calls) == 1


@pytest.mark.django_db
def test_current_includes_evidence_id_when_source_exists(client, monkeypatch):
    EvidenceSource.objects.create(
        evidence_id="E900", provider="Open-Meteo", source_name="Open-Meteo", evidence_type="weather"
    )
    use_payload(monkeypatch, CURRENT_PAYLOAD)
    data = client.get(f"{BASE}/current/?{LOCATION}").json()["data"]
    assert data["evidence_ids"] == ["E900"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        "",
        "latitude=-1.3",
        "longitude=36.8",
        "latitude=95&longitude=36.8",
        "latitude=abc&longitude=36.8",
        "latitude=nan&longitude=36.8",
        "latitude=-1.3&longitude=36.8&country=USA",
        "latitude=51.5&longitude=-0.1",
        "latitude=-1.3&longitude=36.8&country=ETH",
        "region_id=1&latitude=-1.3&longitude=36.8",
    ],
)
def test_current_invalid_params(client, query):
    response = client.get(f"{BASE}/current/?{query}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.django_db
def test_current_provider_failure_returns_clean_503(client, monkeypatch):
    raise_provider_error(monkeypatch)
    response = client.get(f"{BASE}/current/?{LOCATION}")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "secret internal detail" not in response.content.decode()


@pytest.mark.django_db
def test_current_malformed_provider_payload(client, monkeypatch):
    use_payload(monkeypatch, {"unexpected": True})
    assert client.get(f"{BASE}/current/?{LOCATION}").status_code == 503


# ---------- history ----------

HISTORY = f"{BASE}/history/?{LOCATION}&start_date=2020-01-01&end_date=2020-01-02"


@pytest.mark.django_db
def test_history_success(client, monkeypatch):
    calls = []
    use_payload(monkeypatch, archive_payload(), calls)
    data = client.get(HISTORY).json()["data"]

    assert data["data_type"] == "reanalysis"
    assert data["provider"] == "Open-Meteo"
    assert data["retrieved_at"].endswith("Z")
    assert len(data["records"]) == 2

    first, second = data["records"]
    assert first["date"] == "2020-01-01"
    assert first["temperature_mean_c"] == 19.5
    assert first["temperature_min_c"] == 14.0
    assert first["temperature_max_c"] == 26.0
    assert first["precipitation_mm"] == 0.0
    assert first["relative_humidity_percent"] == 50.0
    assert first["data_type"] == "reanalysis"
    assert second["precipitation_mm"] == 3.2
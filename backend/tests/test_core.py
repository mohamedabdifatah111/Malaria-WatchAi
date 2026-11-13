import pytest


@pytest.mark.django_db
def test_health_check_ok(client):
    response = client.get("/api/v1/health/")
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"] == {"status": "ok", "database": "ok"}
    assert body["meta"]["source"] == "malaria-watchai"
    assert body["meta"]["timestamp"].endswith("Z")


def test_unknown_route_returns_json_envelope(client):
    response = client.get("/api/v1/does-not-exist/")
    body = response.json()
    assert response.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.django_db
def test_malformed_json_is_rejected(client):
    response = client.post(
        "/api/v1/health/", data="{bad json", content_type="application/json"
    )
    assert response.status_code in (400, 405)
    assert response.json()["success"] is False
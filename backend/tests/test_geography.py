import pytest
from django.db import IntegrityError, transaction

from apps.geography.models import Country, Region


def make_region(code="KEN", name="Nairobi", level="ADM1", external_id="X1", parent=None):
    return Region.objects.create(
        country=Country.objects.get(code=code),
        name=name,
        admin_level=level,
        external_id=external_id,
        parent=parent,
    )


@pytest.mark.django_db
def test_countries_are_seeded(client):
    response = client.get("/api/v1/countries/")
    body = response.json()
    assert response.status_code == 200
    assert [c["code"] for c in body["data"]] == ["ETH", "KEN", "TZA"]


@pytest.mark.django_db
def test_regions_list_and_filters(client):
    nairobi = make_region(name="Nairobi", external_id="K1")
    make_region(name="Westlands", level="ADM2", external_id="K2", parent=nairobi)
    make_region(code="TZA", name="Arusha", external_id="T1")

    body = client.get("/api/v1/regions/?country=KEN").json()
    assert body["meta"]["pagination"]["count"] == 2

    body = client.get("/api/v1/regions/?country=KEN&level=ADM2").json()
    assert [r["name"] for r in body["data"]] == ["Westlands"]
    assert body["data"][0]["parent_id"] == nairobi.id

    body = client.get("/api/v1/regions/?search=aru").json()
    assert [r["name"] for r in body["data"]] == ["Arusha"]


@pytest.mark.django_db
def test_pagination(client):
    for i in range(3):
        make_region(name=f"R{i}", external_id=f"E{i}")
    body = client.get("/api/v1/regions/?page_size=2").json()
    assert len(body["data"]) == 2
    assert body["meta"]["pagination"]["total_pages"] == 2


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["country=USA", "country=ken", "level=ADM9"])
def test_invalid_filters_return_400(client, query):
    response = client.get(f"/api/v1/regions/?{query}")
    body = response.json()
    assert response.status_code == 400
    assert body["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.django_db
def test_sql_injection_attempt_is_harmless(client):
    make_region()
    response = client.get("/api/v1/regions/?search=' OR 1=1 --")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert Region.objects.count() == 1


@pytest.mark.django_db
def test_region_detail_and_missing(client):
    region = make_region()
    ok = client.get(f"/api/v1/regions/{region.id}/")
    assert ok.status_code == 200
    assert ok.json()["data"]["external_id"] == "X1"

    assert client.get("/api/v1/regions/999999/").status_code == 404
    assert client.get("/api/v1/regions/abc/").status_code == 404


@pytest.mark.django_db
def test_adm1_cannot_have_parent():
    parent = make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_region(name="Bad", external_id="X2", parent=parent)


@pytest.mark.django_db
def test_duplicate_external_id_rejected():
    make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_region(name="Dup")
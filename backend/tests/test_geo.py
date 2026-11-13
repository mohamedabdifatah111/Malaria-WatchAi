import json

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.geography.geojson import to_geojson_geometry
from apps.geography.models import Country, Region
from tests.factories import make_boundary, make_prevalence, make_region, make_source


def signed_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:])) / 2


# ---------- GeoJSON output ----------

def test_geojson_follows_right_hand_rule():
    geometry = to_geojson_geometry(make_boundary(clockwise=True))
    assert geometry["type"] == "MultiPolygon"
    assert signed_area(geometry["coordinates"][0][0]) > 0


def test_geojson_of_none_is_none():
    assert to_geojson_geometry(None) is None


@pytest.mark.django_db
def test_region_detail_includes_boundary(client):
    region = make_region(boundary=make_boundary(clockwise=True))
    boundary = client.get(f"/api/v1/regions/{region.id}/").json()["data"]["boundary"]
    assert boundary["type"] == "MultiPolygon"
    assert signed_area(boundary["coordinates"][0][0]) > 0
    assert "crs" not in boundary


@pytest.mark.django_db
def test_include_boundary_switch(client):
    make_region(boundary=make_boundary())
    default = client.get("/api/v1/regions/").json()["data"][0]
    assert default["boundary"] is not None
    omitted = client.get("/api/v1/regions/?include_boundary=false").json()["data"][0]
    assert "boundary" not in omitted
    assert client.get("/api/v1/regions/?include_boundary=maybe").status_code == 400


@pytest.mark.django_db
def test_country_boundary_is_optional(client):
    plain = client.get("/api/v1/countries/").json()["data"][0]
    assert "boundary" not in plain
    with_boundary = client.get("/api/v1/countries/?include_boundary=true").json()["data"][0]
    assert with_boundary["boundary"] is None


@pytest.mark.django_db
def test_region_page_size_is_capped(client):
    make_region()
    body = client.get("/api/v1/regions/?page_size=200").json()
    assert body["meta"]["pagination"]["page_size"] == 50


@pytest.mark.django_db
def test_spatial_contains_query():
    region = make_region(boundary=make_boundary())
    inside = Region.objects.filter(boundary__contains=Point(36.8, -1.3, srid=4326))
    outside = Region.objects.filter(boundary__contains=Point(39.0, 0.5, srid=4326))
    assert list(inside) == [region]
    assert outside.count() == 0


# ---------- prevalence map ----------

@pytest.mark.django_db
def test_prevalence_map_feature_collection(client):
    source = make_source()
    with_geometry = make_region(boundary=make_boundary(), external_id="K1")
    without_geometry = make_region(name="NoGeometry", external_id="K2")
    make_prevalence(with_geometry, source)
    make_prevalence(without_geometry, source)

    data = client.get("/api/v1/prevalence/map/?country=KEN&year=2020").json()["data"]
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["total_matching"] == 1 and data["truncated"] is False
    feature = data["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "MultiPolygon"
    assert feature["properties"]["estimate"] == 0.12
    assert feature["properties"]["evidence_ids"] == ["E001"]


@pytest.mark.django_db
def test_prevalence_map_resolution_filter_and_empty(client):
    source = make_source()
    make_prevalence(make_region(boundary=make_boundary()), source)
    data = client.get("/api/v1/prevalence/map/?resolution=ADM2").json()["data"]
    assert data["features"] == []
    assert data["data_status"] == "no_data"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query", ["resolution=ADM9", "year=abc", "country=USA", "indicator=bad;drop", "source_type=guess"]
)
def test_prevalence_map_invalid_params(client, query):
    assert client.get(f"/api/v1/prevalence/map/?{query}").status_code == 400


# ---------- boundary importer ----------

def square(west=36.7, south=-1.4, east=36.9, north=-1.2):
    return [[[west, south], [east, south], [east, north], [west, north], [west, south]]]


def feature(shape_id, name, geometry=None, **props):
    geometry = geometry or {"type": "Polygon", "coordinates": square()}
    return {
        "type": "Feature",
        "properties": {"shapeID": shape_id, "shapeName": name, **props},
        "geometry": geometry,
    }


def write(tmp_path, features, name="boundaries.geojson"):
    path = tmp_path / name
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return str(path)


def run(path, *extra, level="ADM1", country="KEN"):
    call_command("import_boundaries", path, "--country", country, "--level", level, *extra)


@pytest.mark.django_db
def test_import_adm1_creates_then_updates(tmp_path):
    run(write(tmp_path, [feature("K1", "Nairobi")]))
    region = Region.objects.get(external_id="K1")
    assert region.name == "Nairobi"
    assert region.boundary.srid == 4326
    assert region.boundary.geom_type == "MultiPolygon"

    run(write(tmp_path, [feature("K1", "Nairobi County")]))
    assert Region.objects.count() == 1
    assert Region.objects.get().name == "Nairobi County"


@pytest.mark.django_db
def test_import_adm0_sets_country_boundary(tmp_path):
    run(write(tmp_path, [feature("K0", "Kenya")]), level="ADM0")
    assert Country.objects.get(code="KEN").boundary is not None


@pytest.mark.django_db
def test_import_adm2_links_parent(tmp_path):
    run(write(tmp_path, [feature("K1", "Nairobi")]))
    child = feature(
        "K2", "Westlands",
        geometry={"type": "Polygon", "coordinates": square(36.75, -1.35, 36.85, -1.25)},
        parentID="K1",
    )
    run(write(tmp_path, [child], "adm2.geojson"), "--parent-id-field", "parentID", level="ADM2")
    assert Region.objects.get(external_id="K2").parent.external_id == "K1"


@pytest.mark.django_db
def test_import_rejects_wrong_geometry_type(tmp_path):
    point = {"type": "Point", "coordinates": [36.8, -1.3]}
    with pytest.raises(CommandError):
        run(write(tmp_path, [feature("K1", "Nairobi", geometry=point)]))
    assert Region.objects.count() == 0


@pytest.mark.django_db
def test_import_rejects_geometry_outside_country(tmp_path):
    london = {"type": "Polygon", "coordinates": square(-0.2, 51.4, 0.1, 51.6)}
    with pytest.raises(CommandError):
        run(write(tmp_path, [feature("K1", "Nowhere", geometry=london)]))
    assert Region.objects.count() == 0


@pytest.mark.django_db
def test_import_rejects_missing_id_property(tmp_path):
    bad = {"type": "Feature", "properties": {"other": "x"},
           "geometry": {"type": "Polygon", "coordinates": square()}}
    with pytest.raises(CommandError):
        run(write(tmp_path, [bad]))


@pytest.mark.django_db
def test_import_is_all_or_nothing(tmp_path):
    point = {"type": "Point", "coordinates": [36.8, -1.3]}
    with pytest.raises(CommandError):
        run(write(tmp_path, [feature("K1", "Good"), feature("K2", "Bad", geometry=point)]))
    assert Region.objects.count() == 0


@pytest.mark.django_db
def test_import_dry_run_writes_nothing(tmp_path):
    run(write(tmp_path, [feature("K1", "Nairobi")]), "--dry-run")
    assert Region.objects.count() == 0


@pytest.mark.django_db
def test_import_rejects_duplicate_ids(tmp_path):
    with pytest.raises(CommandError):
        run(write(tmp_path, [feature("K1", "A"), feature("K1", "B")]))


@pytest.mark.django_db
def test_import_rejects_wrong_file_type(tmp_path):
    path = tmp_path / "boundaries.txt"
    path.write_text("{}")
    with pytest.raises(CommandError):
        run(str(path))


@pytest.mark.django_db
def test_import_invalid_geometry_needs_repair(tmp_path):
    bowtie = {"type": "Polygon", "coordinates": [[[36.0, 0.0], [37.0, 1.0], [37.0, 0.0], [36.0, 1.0], [36.0, 0.0]]]}
    path = write(tmp_path, [feature("K1", "Bowtie", geometry=bowtie)])
    with pytest.raises(CommandError):
        run(path)
    run(path, "--repair")
    assert Region.objects.get(external_id="K1").boundary.valid
import json


def _signed_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:])) / 2


def _orient(rings):
    """RFC 7946 right-hand rule: exterior ring counter-clockwise, holes clockwise."""
    oriented = []
    for index, ring in enumerate(rings):
        counter_clockwise = _signed_area(ring) > 0
        if counter_clockwise == (index == 0):
            oriented.append(ring)
        else:
            oriented.append(list(reversed(ring)))
    return oriented


def to_geojson_geometry(geom):
    """GeoJSON geometry (EPSG:4326, longitude then latitude) or None."""
    if geom is None:
        return None
    data = json.loads(geom.json)
    data.pop("crs", None)
    if data["type"] == "Polygon":
        data["coordinates"] = _orient(data["coordinates"])
    elif data["type"] == "MultiPolygon":
        data["coordinates"] = [_orient(polygon) for polygon in data["coordinates"]]
    return data
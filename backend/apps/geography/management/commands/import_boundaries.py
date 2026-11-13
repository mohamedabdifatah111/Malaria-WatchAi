import json
from pathlib import Path

from django.contrib.gis.geos import GEOSException, GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.environment.bounds import BOUNDS
from apps.geography.models import Country, Region

MAX_FILE_BYTES = 200 * 1024 * 1024
MAX_FEATURES = 5000
ALLOWED_SUFFIXES = {".geojson", ".json"}


def _load_features(file):
    path = Path(file)
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise CommandError("Only .geojson or .json files are accepted.")
    if not path.is_file():
        raise CommandError("File not found.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise CommandError("File is too large.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError("The file is not valid JSON.") from exc
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
    ):
        raise CommandError("Expected a GeoJSON FeatureCollection.")
    if not 1 <= len(data["features"]) <= MAX_FEATURES:
        raise CommandError(f"The file must contain between 1 and {MAX_FEATURES} features.")
    return data["features"]


def _polygons(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        found = []
        for part in geom:
            found.extend(_polygons(part))
        return found
    return []


def _geometry(feature, country, repair, label):
    raw = feature.get("geometry")
    if not isinstance(raw, dict) or raw.get("type") not in ("Polygon", "MultiPolygon"):
        raise CommandError(f"{label}: geometry must be a Polygon or MultiPolygon.")
    try:
        geom = GEOSGeometry(json.dumps(raw), srid=4326)
    except (GEOSException, ValueError, TypeError) as exc:
        raise CommandError(f"{label}: geometry could not be read.") from exc
    geom.srid = 4326
    if geom.empty:
        raise CommandError(f"{label}: geometry is empty.")
    if not geom.valid:
        if not repair:
            raise CommandError(
                f"{label}: geometry is invalid ({geom.valid_reason}). Use --repair to attempt a fix."
            )
        geom = geom.make_valid()
    polygons = _polygons(geom)
    if not polygons:
        raise CommandError(f"{label}: no polygon geometry remains after validation.")
    geom = MultiPolygon(*polygons, srid=4326)

    lat_min, lat_max, lon_min, lon_max = BOUNDS[country]
    xmin, ymin, xmax, ymax = geom.extent
    if xmin < lon_min or xmax > lon_max or ymin < lat_min or ymax > lat_max:
        raise CommandError(f"{label}: geometry lies outside {country}.")
    return geom


def _text(props, field, label, limit):
    value = props.get(field)
    if value is None or str(value).strip() == "":
        available = ", ".join(sorted(props)) or "none"
        raise CommandError(f"{label}: missing property '{field}'. Available properties: {available}.")
    value = str(value).strip()
    if len(value) > limit:
        raise CommandError(f"{label}: property '{field}' is longer than {limit} characters.")
    return value


class Command(BaseCommand):
    help = (
        "Import administrative boundaries from a GeoJSON FeatureCollection (EPSG:4326). "
        "All-or-nothing. Check your file's property names; the defaults are only defaults."
    )

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--country", required=True, choices=["KEN", "TZA", "ETH"])
        parser.add_argument("--level", required=True, choices=["ADM0", "ADM1", "ADM2"])
        parser.add_argument("--id-field", default="shapeID")
        parser.add_argument("--name-field", default="shapeName")
        parser.add_argument("--parent-id-field", default="")
        parser.add_argument("--repair", action="store_true", help="Attempt to repair invalid geometry.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report, write nothing.")

    def handle(self, *args, **options):
        country = Country.objects.filter(code=options["country"]).first()
        if country is None:
            raise CommandError("Countries are not seeded. Run migrate first.")
        level = options["level"]
        parent_field = options["parent_id_field"]
        if parent_field and level != "ADM2":
            raise CommandError("--parent-id-field only applies to --level ADM2.")

        features = _load_features(options["file"])
        records, seen = [], set()
        for index, feature in enumerate(features, start=1):
            label = f"Feature {index}"
            if not isinstance(feature, dict):
                raise CommandError(f"{label}: not a valid feature.")
            geom = _geometry(feature, options["country"], options["repair"], label)
            if level == "ADM0":
                records.append({"geometry": geom})
                continue
            props = feature.get("properties")
            if not isinstance(props, dict):
                raise CommandError(f"{label}: missing properties.")
            external_id = _text(props, options["id_field"], label, 100)
            name = _text(props, options["name_field"], label, 200)
            if external_id in seen:
                raise CommandError(f"{label}: duplicate id '{external_id}' in the file.")
            seen.add(external_id)
            parent = _text(props, parent_field, label, 100) if parent_field else None
            records.append(
                {"geometry": geom, "external_id": external_id, "name": name, "parent": parent}
            )

        created = updated = 0
        with transaction.atomic():
            if level == "ADM0":
                union = records[0]["geometry"]
                for record in records[1:]:
                    union = union.union(record["geometry"])
                country.boundary = MultiPolygon(*_polygons(union), srid=4326)
                country.save(update_fields=["boundary", "updated_at"])
                updated = 1
            else:
                for record in records:
                    defaults = {"name": record["name"], "boundary": record["geometry"]}
                    if parent_field:
                        parent = Region.objects.filter(
                            country=country, admin_level="ADM1", external_id=record["parent"]
                        ).first()
                        if parent is None:
                            raise CommandError(
                                f"Parent ADM1 region '{record['parent']}' was not found. "
                                "Import ADM1 first."
                            )
                        defaults["parent"] = parent
                    _, was_created = Region.objects.update_or_create(
                        country=country,
                        admin_level=level,
                        external_id=record["external_id"],
                        defaults=defaults,
                    )
                    created += was_created
                    updated += not was_created
            if options["dry_run"]:
                transaction.set_rollback(True)

        prefix = "DRY RUN (nothing saved): " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{created} created, {updated} updated."))
"""Load ML pipeline outputs into the database.

    python manage.py import_ml_outputs                 # reads <repo>/data/processed
    python manage.py import_ml_outputs --dry-run       # map and validate, write nothing
    python manage.py import_ml_outputs --processed-dir path/to/data/processed

Prerequisites
  1. ML outputs built: `python -m ml.src.pipeline` (repo root).
  2. Boundaries imported with geoBoundaries ids, e.g. for each country/level:
       python manage.py import_boundaries ../data/raw/boundaries/geoBoundaries-KEN-ADM1.geojson \
           --country KEN --level ADM1 --id-field shapeID
     (ADM1 before ADM2). ML rows are matched to Region.external_id = shapeID.

Re-running replaces everything this command imported before (rows whose evidence
source carries an ML-assigned id, E10001 and above), so the command is
idempotent. Rows whose region is not in the database are skipped and reported.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.ml_import import Mapper
from apps.drug_efficacy.models import DrugEfficacyRecord
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region
from apps.population.models import PopulationAtRisk
from apps.prevalence.models import PrevalenceEstimate, PrevalenceObservation
from apps.resistance.models import Marker, MarkerTrend, ResistanceObservation
from apps.species.models import SpeciesRecord

ML_ID_MIN = 10001
MODELS = [  # children first, so deletes respect PROTECT foreign keys
    ("prevalence_estimate", PrevalenceEstimate),
    ("prevalence_observation", PrevalenceObservation),
    ("population_at_risk", PopulationAtRisk),
    ("species", SpeciesRecord),
    ("drug_efficacy", DrugEfficacyRecord),
    ("resistance_observation", ResistanceObservation),
    ("marker_trend", MarkerTrend),
]


def _is_ml_evidence(evidence_id: str) -> bool:
    return evidence_id[1:].isdigit() and int(evidence_id[1:]) >= ML_ID_MIN


class Command(BaseCommand):
    help = "Import ML outputs (data/processed/*.parquet) into prevalence, population, species, efficacy and resistance tables."

    def add_arguments(self, parser):
        default = Path(settings.BASE_DIR).parent / "data" / "processed"
        parser.add_argument("--processed-dir", default=str(default))
        parser.add_argument("--dry-run", action="store_true", help="Map and validate only; write nothing.")

    def handle(self, *args, **opts):
        processed = Path(opts["processed_dir"])
        if not (processed / "evidence.parquet").exists():
            raise CommandError(f"{processed} has no ML outputs; run `python -m ml.src.pipeline` first.")
        mapper = Mapper(processed)
        built = mapper.build()
        report = mapper.report(built)
        if opts["dry_run"]:
            self.stdout.write(json.dumps(report, indent=1))
            self.stdout.write(self.style.WARNING("Dry run: nothing written."))
            return
        with transaction.atomic():
            written, unresolved = self._write(built)
        for t, n in written.items():
            report[t]["written"] = n
        for t, n in unresolved.items():
            report[t]["skipped"]["region_not_in_database"] = n
        self.stdout.write(json.dumps(report, indent=1))
        if any(unresolved.values()):
            self.stdout.write(self.style.WARNING(
                "Some rows reference regions that are not imported; run import_boundaries with --id-field shapeID."))
        self.stdout.write(self.style.SUCCESS("ML outputs imported."))

    # ------------------------------------------------------------------ write
    def _write(self, built):
        countries = {c.code: c for c in Country.objects.all()}
        missing_countries = {"KEN", "TZA", "ETH"} - set(countries)
        if missing_countries:
            raise CommandError(f"Countries missing from the database: {sorted(missing_countries)}")
        regions = {(r.country.code, r.admin_level, r.external_id): r
                   for r in Region.objects.select_related("country")}

        # 1) remove previously imported ML rows (children first), then ML evidence
        ml_sources = [e.pk for e in EvidenceSource.objects.all() if _is_ml_evidence(e.evidence_id)]
        for _, model in MODELS:
            model.objects.filter(source_id__in=ml_sources).delete()

        # 2) evidence (update in place so foreign keys elsewhere stay valid)
        sources = {}
        for row in built["evidence"]:
            eid = row.pop("evidence_id")
            obj, _ = EvidenceSource.objects.update_or_create(evidence_id=eid, defaults=row)
            sources[eid] = obj

        markers = {}
        for row in built["marker"]:
            obj, _ = Marker.objects.update_or_create(name=row["name"], defaults={
                "gene": row["gene"], "description": row["description"]})
            markers[row["name"]] = obj

        written, unresolved = {}, {}
        for table, model in MODELS:
            objs, miss = [], 0
            for row in built[table]:
                row = dict(row)
                row["country"] = countries[row["country"]]
                ref = row.pop("region", None)
                if ref is not None:
                    region = regions.get(ref)
                    if region is None:
                        miss += 1
                        continue
                    row["region"] = region
                row["source"] = sources[row["source"]]
                if "marker" in row:
                    row["marker"] = markers[row["marker"]]
                objs.append(model(**row))
            model.objects.bulk_create(objs, batch_size=1000)
            written[table], unresolved[table] = len(objs), miss
        return written, unresolved

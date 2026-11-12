# Malaria WatchAI - ML pipeline

Prevalence modelling, uncertainty, population at risk, species evidence, drug
efficacy and resistance-marker analysis for Kenya, Tanzania and Ethiopia.
Research and programme-planning tool - not for diagnosis or treatment.

## Run

```bash
pip install -r requirements.txt
python -m mal.fetch                 # data layer: downloads data/raw + data/manifest.csv
python -m ml.src.pipeline           # all ML stages (~6 min; first run builds a covariate cache)
python -m pytest ml/tests           # unit tests + output contract tests
```

Resume or run single stages:

```bash
python -m ml.src.pipeline --from evaluate
python -m ml.src.pipeline --only species efficacy resistance evidence
python -m ml.src.pipeline --refresh-covariates   # rebuild data/interim/covariates_5km.npz
```

Raw data in another checkout (e.g. a git worktree): set `MAL_RAW_DIR` to that
checkout's `data/raw`.

Stages: `surveys -> features -> evaluate -> predict -> pop_at_risk -> species ->
efficacy -> resistance -> evidence`. The evidence stage fails the run if any
output cites an `evidence_id` missing from the registry.

## Configuration

- `config.yaml` (repo root, shared): seed, CRS, 5 km grid, survey years, paths.
- `ml/config/ml_config.yaml`: countries, features, model, validation, uncertainty,
  risk classes, drugs, resistance markers. Every output stores a hash of both files.

## Outputs (`data/processed/`)

All prevalence values are **proportions 0-1**; efficacy is **%**; populations are
**persons**. Missing values are null - never imputed. `status` is one of `ok`,
`extrapolated`, `insufficient_data`, `excluded_from_pooling`, `presence_only`,
`not_recommended`. Every row has `evidence_ids` that resolve in `evidence.parquet`.
Each Parquet file carries run metadata (model version, generated_at, config hash)
in its schema metadata key `malaria_watchai`.

| File | API | Content |
|---|---|---|
| `surveys.parquet` (GeoParquet) | 4.2 observed | Cleaned PfPR surveys: examined, positive, prevalence, age band, method, ADM1/ADM2 ids, source |
| `surveys_pv.parquet` (GeoParquet) | 4.4 | Cleaned PvPR surveys |
| `grid_2020.parquet` | - | 5 km cells with covariates and prediction defaults |
| `prevalence_grid.parquet` (GeoParquet, EPSG:4326) | 4.2 map | Cell estimate, prevalence interval, survey interval, distance to survey, extrapolation flag, reliability |
| `prevalence_district.parquet` | 4.2 | ADM0/1/2 rows: `source_type=modelled` (2020, PfPR 2-10) and `observed` (pooled survey prevalence per year) |
| `prevalence_uncertainty.parquet` | 4.2 uncertainty | Interval, width, nearest survey km, survey density, extrapolation flag, reliability |
| `prevalence_adm1.geojson`, `prevalence_adm2.geojson` | map | Modelled district values, simplified polygons, EPSG:4326 |
| `pop_at_risk.parquet` | 4.3 | Population per risk class per ADM0/1/2, plus lower/upper-bound scenarios |
| `species.parquet` | 4.4 | Survey, country-report, presence-only and no-evidence rows for the five species |
| `efficacy_studies.parquet` | 4.5 | One row per WHO TES study (ACPR %, Wilson CI, follow-up, N) |
| `efficacy_pooled.parquet` | 4.5 | Random-effects pools per country x drug x follow-up (CI, PI, I2, tau2, study count) |
| `marker_observations.parquet` | 4.6 | Marker frequency per site/ADM1 x year with n tested, n mutant, Wilson CI |
| `marker_trends.parquet` | 4.6 trends | Observed and fitted frequency per country x year, validation method, status |
| `marker_predictions.parquet` | 4.6 trends | Held-out validation rows and 2020 forecasts (flagged) |
| `evidence.parquet`, `evidence.json` | 6 | Evidence registry (dataset + record level) |
| `metrics.json` | 7 | CV metrics for all schemes/models, comparison vs baselines, interval coverage |
| `model_metadata.json` | 7 | Model type, version, features, hyperparameters, importance, training data, temporal note |

`ml/outputs/` (gitignored, rebuilt): `survey_validation.json` (records dropped per
rule), `feature_qa.json` (covariate gaps, population conservation),
`oof_predictions.parquet`, `model_pfpr.joblib`, `pipeline_run.json`.

## Agent tools

`ml/src/lookup.py` provides `prevalence_lookup`, `population_at_risk`,
`species_lookup`, `drug_evidence_lookup` and `resistance_lookup`. Each returns
values with units, intervals, sample sizes, evidence ids, a data status and
limitations; unknown places return `not_found` and missing evidence returns
`insufficient_data`.

## Code map

```
ml/src/data/          boundaries.py, surveys.py (cleaning + validation report)
ml/src/features/      grid.py (5 km grid), covariates.py, build.py
ml/src/models/        baseline.py (IDW, ADM1 mean), lgbm.py, uncertainty.py, predict.py, pop_at_risk.py
ml/src/evaluation/    spatial_cv.py, metrics.py, evaluate.py
ml/src/species/       species.py
ml/src/drug_efficacy/ meta.py (DerSimonian-Laird), efficacy.py
ml/src/resistance/    markers.py, trends.py
ml/src/evidence.py    registry + integrity check
ml/src/lookup.py      agent-facing lookups
ml/src/pipeline.py    entry point
```

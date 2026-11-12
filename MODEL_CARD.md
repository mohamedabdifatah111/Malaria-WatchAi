# Model card - Malaria WatchAI PfPR model v0.1.0

Machine-readable details: `data/processed/model_metadata.json` and `metrics.json`.
Scientific assumptions: `ASSUMPTIONS.md`. Pipeline: `ml/README.md`.

## Intended use

- Support malaria programme planners and researchers in Kenya, Tanzania and
  Ethiopia: where *P. falciparum* prevalence is likely higher or lower, how many
  people live in each prevalence class, and where the evidence is thin.
- Provide cited, uncertainty-labelled values to the Malaria WatchAI assistant
  through backend tools.

## Prohibited use

- Individual diagnosis, treatment or dosing decisions.
- Presenting modelled values as observed measurements.
- Treating population-at-risk figures as numbers of infected people.
- Treating resistance-marker frequencies as treatment-failure rates, or a 10%
  failure signal as an automatic treatment-policy change.
- Using estimates flagged `extrapolated` without stating so.

## Model

| Item | Value |
|---|---|
| Model | LightGBM gradient-boosted trees (regression), seed 42, deterministic |
| Target | Empirical logit of survey PfPR; output back-transformed to a proportion |
| Prediction | PfPR, ages 2-10, microscopy, year 2020, 5 km cells (ESRI:102022), aggregated to ADM0/ADM1/ADM2 by WorldPop 2020 population |
| Weights | min(examined, 500) |
| Features | temperature mean and seasonality, annual rainfall and seasonality (WorldClim 1970-2000), elevation, NDVI 2020, log population density, urban class (GHSL), distance to water, survey year, lower/upper age, RDT flag |
| Not used | raw longitude/latitude |
| Baselines | inverse-distance weighting (15 neighbours, power 2); ADM1 pooled mean |

## Training data

2,555 open MAP PfPR surveys, 2000-2021 (Kenya 1,260; Tanzania 1,181;
Ethiopia 114), after removing 6,249 records withheld by MAP, 656 pre-2000
records and 9 duplicates. Latest open survey year: Kenya 2016, Tanzania 2016,
Ethiopia 2021.

## Validation design

- **Primary: 5-fold spatial block cross-validation** (100 km blocks; whole blocks held out).
- Leave-one-ADM1-out.
- Random 5-fold - **comparison only** (optimistic: neighbouring surveys share folds).
- Errors on the prevalence scale (proportion 0-1), per survey.

## Performance (all 2,555 surveys, out-of-fold)

| Scheme | Model | MAE | RMSE | Spearman |
|---|---|---|---|---|
| Spatial block 5-fold | IDW | 0.156 | 0.212 | 0.60 |
| Spatial block 5-fold | ADM1 mean | 0.163 | 0.231 | 0.48 |
| Spatial block 5-fold | **LightGBM** | **0.119** | **0.174** | **0.71** |
| Leave-one-ADM1-out | IDW | 0.162 | 0.232 | 0.52 |
| Leave-one-ADM1-out | ADM1 mean | 0.202 | 0.274 | 0.10 |
| Leave-one-ADM1-out | **LightGBM** | **0.130** | **0.195** | **0.67** |
| Random 5-fold (comparison) | IDW | 0.111 | 0.167 | 0.76 |
| Random 5-fold (comparison) | ADM1 mean | 0.134 | 0.192 | 0.68 |
| Random 5-fold (comparison) | LightGBM | 0.085 | 0.127 | 0.85 |

LightGBM beats both baselines under every scheme. Under spatial validation the
typical error is still about 12 percentage points of prevalence per survey, and
the gap between random and spatial CV shows how much accuracy drops away from
surveyed areas. Metrics by country, decade and prevalence band are in `metrics.json`.

## Uncertainty

- 90% intervals from distance-stratified conformal calibration on spatial-block
  out-of-fold residuals, with survey sampling noise separated from model error.
- Survey-level coverage (cross-validated): about 96% (target 90%).
- Prevalence-interval coverage on the 51 surveys with >= 500 examined: about 82%
  (target 90%) - intervals for true prevalence are somewhat **too narrow**; treat as
  approximate.
- Intervals are wide (mean width about 0.5 on the prevalence scale), which is why
  population-at-risk lower/upper scenarios differ a lot from the central estimate.
- Each cell and region carries `nearest_survey_distance_km`, survey density,
  an `extrapolation_flag` (> 100 km from any survey, or covariates outside the
  training range) and `reliability_status` (`ok` / `low` / `extrapolated`).
  About 47% of cells are `extrapolated`; Ethiopia is `extrapolated` nationally.

## Known limitations

- **Temporal:** 2020 predictions carry forward the latest open survey years
  (2016 for Kenya and Tanzania); trees cannot extrapolate a trend after 2016.
- **Geographic:** Ethiopia has only 114 open surveys (53% with zero positives);
  most of it is far from any survey.
- **Data access:** two-thirds of MAP records, including most DHS/MIS clusters, are
  withheld; the open set is not a representative sample.
- **Covariates:** climate is a 1970-2000 climatology; NDVI, population and
  urbanisation are 2020 values applied to all survey years.
- **Spatial structure:** no explicit spatial random effect; residual spatial
  correlation is only partly captured by covariates.
- **Age/diagnostics:** handled as features, not by a published age-standardisation
  model.

## Generalisation risks

Do not apply outside Kenya, Tanzania and Ethiopia, to years far from 2000-2016,
or to settings with large changes in interventions since the last surveys (e.g.
bed-net campaigns, seasonal malaria chemoprevention), without new data and
re-validation.

## Other analyses in this release

- **Drug efficacy (WHO Threats Map TES):** DerSimonian-Laird random-effects pools
  of PCR-corrected ACPR per country x drug x follow-up (>= 3 studies). AL day-28:
  Kenya 96.9% (95% CI 93.8-98.4; 8 studies, 927 patients), Tanzania 97.0%
  (95.3-98.1; 15 studies, 1,100 patients), Ethiopia 97.3% (96.4-98.0; 27 studies,
  2,149 patients). No AL day-42 pool (no studies).
- **Resistance markers (WHO Threats Map + Pf7):** binomial GLM trends by country.
  In held-out-year and held-out-region validation the GLM did **not** beat the
  last-observed or country-average baselines; forecasts are therefore marked
  `not_recommended`, and the latest observed frequency should be preferred.
- **Species:** evidence summary only (no model) - see `ASSUMPTIONS.md`.

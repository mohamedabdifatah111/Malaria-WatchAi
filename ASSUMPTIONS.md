# Assumptions and limitations

Scientific assumptions behind the Malaria WatchAI ML outputs. Numbers quoted here
come from the pipeline run recorded in `data/processed/metrics.json` and
`ml/outputs/*.json`; re-check them after any re-run.

## Survey data (MAP parasite-rate surveys, release 202406)

- **Only released records are used.** MAP withholds coordinates or values for
  most points in the study countries (PfPR: 6,249 of 9,469 records withheld).
  Withheld points are often DHS/MIS clusters, so the open data under-represent
  national household surveys.
- **Analysis period 2000-2024** (shared `config.yaml`). 656 PfPR records before
  2000 are excluded.
- **The newest open surveys are old.** Latest open PfPR survey year: Kenya 2016,
  Tanzania 2016, Ethiopia 2021. A 2020 prediction from tree models carries the
  latest observed level forward; it is not an observed 2020 value.
- **Sampling bias.** Surveys are purposive (schools, research sites, endemic
  foci), cluster in western Kenya, north-east Tanzania and parts of Ethiopia, and
  over-represent higher-transmission areas.
- **Duplicates.** Rows identical in country, coordinates (4 dp), start
  year/month, age band, examined and positives are counted once (lowest MAP id kept).
- **Coordinates.** Points up to 5 km outside their stated country polygon are kept
  (coastal/border geocoding precision) and given the nearest region.
- **Year** is the survey start year.

## Age and diagnostics

- Surveys span different age bands and diagnostics (microscopy, RDT, RDT
  confirmed by microscopy). These are **not** converted with an external
  age-standardisation formula. Instead the age bounds and an RDT flag are model
  features, and predictions are made for **ages 2-10, microscopy** (the MAP
  convention). This assumes the model learns age/diagnostic effects from the data.
- Observed rows in `prevalence_district.parquet` are pooled across whatever ages
  and methods were surveyed and are labelled `age_band = "as surveyed (mixed)"`.

## Target transformation and weighting

- Target: empirical logit `log((y+0.5)/(n-y+0.5))`, finite at 0% and 100%.
- Weight: `min(examined, 500)`. Larger surveys count more; the cap stops a
  handful of very large surveys from dominating.

## Environmental covariates

| Covariate | Source | Temporal status |
|---|---|---|
| Mean temperature, temperature seasonality, annual rainfall, rainfall seasonality | WorldClim 2.1 | **1970-2000 climatology**, not 2020 weather |
| Elevation | WorldClim 2.1 (SRTM-derived) | static |
| NDVI | MODIS MOD13A1, 2020 annual median | 2020 only, applied to all survey years |
| Population density | WorldPop 2020 UN-adjusted | 2020 only, applied to all survey years |
| Urban/rural class | GHSL SMOD 2020 | 2020 only |
| Distance to water | HydroRIVERS (Strahler >= 3) + Natural Earth lakes | static |

- Covariates are averaged to 5 km cells (Africa Albers Equal Area, ESRI:102022);
  a survey takes the values of the cell it falls in. Distance to water is computed
  at the exact point in Africa Equidistant Conic (ESRI:102023).
- Applying 2020 NDVI/population/urbanisation to older surveys assumes these
  change slowly relative to prevalence. That is not true everywhere (urban growth).
- Small streams, seasonal pools, irrigation and dams are not in the water layer.

## Spatial interpolation and extrapolation

- Raw longitude/latitude are **not** features; spatial structure must come from
  covariates. Residual spatial correlation is therefore not modelled explicitly.
- A 5 km cell is flagged `extrapolated` when it is > 100 km from any survey or any
  environmental covariate lies outside the 0.5-99.5% range of the training surveys.
  `low` reliability = > 25 km from any survey.
- Regions smaller than one 5 km cell (9 ADM2 units) take the value of the nearest
  cell; their population is left unknown (`aggregation_method` column).

## Uncertainty

- Prediction intervals come from spatial-block out-of-fold residuals, stratified by
  distance to the nearest training survey (conformal calibration).
- Survey sampling (binomial) noise is separated from model error by method of
  moments; it accounted for roughly 20-38% of residual variance. The
  **prevalence interval** (maps, districts, population at risk) uses model error;
  the **survey prediction interval** (grid columns `survey_pi_*`) also includes
  sampling noise.
- Interval multiplier = max(all-survey calibration, large-survey calibration),
  because large surveys (>= 500 examined) directly test the prevalence interval.
  Cross-validated coverage of the prevalence interval on those 51 surveys is
  below the 90% target (see `metrics.json`); treat intervals as approximate.
- District intervals average cell bounds (population-weighted). This assumes
  cell errors are fully correlated within a district - conservative.

## Population at risk

- WorldPop 2020 1 km counts are summed into 5 km cells by pixel centre; pixels
  whose centre lands in the sea, a lake or a neighbouring country are moved to the
  nearest cell of their own country, so country totals equal the WorldPop totals.
- Populations are counts of **people living where modelled PfPR falls in a class**,
  never infected people.
- The lower/upper scenario columns reclassify the same population using interval
  bounds. They are wide because model uncertainty is large.

## Species

- No species distribution model is fitted: open denominator-bearing data are too
  sparse (158 P. vivax survey points, none for P. malariae / P. ovale).
- GBIF records are presence-only (mostly genomic samples) and never produce shares.
- WHO GHO reported indigenous Pf/Pv cases give country-level shares of *reported*
  cases only; they depend on testing and reporting completeness.
- Microscopy under-detects low-density and mixed infections and misclassifies
  P. ovale / P. malariae / P. knowlesi.
- National microscopy species shares are hand-entered in
  `data/raw/species/mis_microscopy_manual.csv` (values are % of microscopy-positive
  people, with the report page). Entered: **Kenya MIS 2020, Table 4.9** (588
  malaria-positive children 6 months-14 years: Pf only 75.9%, Pm only 3.7%, Po only
  0.7%, mixed 19.6%, no P. vivax). These are national values and are never applied
  to districts.
- **Tanzania MIS 2017** tested by RDT only (Pf/Pan), which cannot identify
  P. malariae or P. ovale - recorded as `insufficient_data` with that reason.
  **Ethiopia**: no national microscopy species table has been entered yet.
- No evidence was found for P. knowlesi in the three countries.

## Survey priority (where to survey next)

- Each ADM2 district gets one hypothetical survey at its population-weighted
  centre; the reduction in sum(population x interval width) across all cells is
  computed from the calibrated distance bands of the prevalence interval.
- It reflects only the model's distance-based uncertainty. It ignores cost,
  access, security, seasonality, altitude-based expert knowledge (e.g. Addis Ababa
  ranks high because it is populous and far from open surveys, although
  transmission there is low) and non-public programme data. It is a planning aid
  for discussion, not a survey design.
- 9 ADM2 districts smaller than one 5 km cell are not ranked.

## AI briefing grounding

- `check_brief` treats any number not present in tool results as unsupported,
  including numbers the agent computed itself. Short numbers (1-2 significant
  digits) may match a tool value by coincidence; they are labelled `weak` with the
  matched field names for human review. The check does not verify wording, units
  or which place a number belongs to - human approval remains required.

## Drug efficacy

- Source: WHO Malaria Threats Map therapeutic efficacy studies (P. falciparum).
- **To verify:** `TREATMENT_FAILURE_PP` is taken as the per-protocol,
  PCR-corrected failure proportion published by the Threats Map. Failure counts are
  reconstructed as `round(proportion x N)`.
- Studies with unknown follow-up are listed but never pooled. Day-28 and day-42
  are pooled separately; pooling needs >= 3 studies.
- Random-effects (DerSimonian-Laird) on the logit scale with a 0.5 continuity
  correction for 0 failures; this pulls very low failure rates slightly upward, so
  a crude pooled rate is reported alongside.
- Study sites are purposive; a pooled value describes those sites. Pools covering
  <= 2 ADM1 regions are flagged as geographically concentrated.
- The WHO 10% failure threshold is a signal for policy review, not a recommendation.

## Resistance markers

- Sources: WHO Threats Map pfkelch13 studies (with genotype detail) and MalariaGEN
  Pf7 sample genotypes (pfcrt K76T, pfmdr1 copy number, pfkelch13).
- Validated pfkelch13 list = WHO 2020 report Table 4. Newer WHO lists may differ.
- WHO Threats Map studies with no genotype rows are excluded (69 of 161 in scope):
  a missing genotype row is not evidence of zero mutants.
- Pf7 samples are located to ADM1 centroids, cluster in a few sites (e.g. Kilifi,
  Tanga, Kigoma) and end around 2015.
- Mixed pfcrt K/T infections count as carrying the mutant.
- Trend GLMs that hit perfect separation are not reported. In validation the GLM
  did **not** beat the last-observed or country-average baselines, so forecasts are
  marked `not_recommended`.
- A marker frequency is not a clinical treatment-failure rate.

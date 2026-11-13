# MalariaWatchAI

## DATA REFERENCE DOCUMENT

**Project:** MalariaWatchAI  
**Challenge:** Malaria Atlas Lab  
**Geographic Coverage:** Kenya, Tanzania and Ethiopia  
**Purpose:** Shared data reference for Backend, Frontend, Machine Learning and AI Engineering teams.

> This is the team's central, hand-maintained data reference. The per-file download
> manifest (URLs, SHA-256 checksums, access times) is generated separately by
> `python -m mal.fetch` into [docs/DATA_MANIFEST.md](docs/DATA_MANIFEST.md).
> Section 15 lists every dataset currently downloaded or used, as required by section 13.

---

## 1. Purpose of this document

This document establishes a common reference for all datasets used or proposed for MalariaWatchAI.

Every team member must follow these data standards to ensure consistency, scientific credibility, reproducibility and reliable integration.

It documents:

- Data sources and providers.
- Geographic coverage.
- Data formats and variables.
- Data quality requirements.
- Licensing and attribution considerations.
- Data limitations and assumptions.
- Integration requirements.

**Important:** A dataset being documented here does not mean it has already been downloaded, imported, validated or integrated.

---

## 2. Geographic coverage

The platform initially focuses on three East African countries:

| Country | ISO code |
|---|---|
| Kenya | KEN |
| Tanzania | TZA |
| Ethiopia | ETH |

All geographic datasets should use consistent country identifiers and administrative boundaries.

Preferred geographic hierarchy:

1. Country.
2. Administrative level 1 (ADM1).
3. Administrative level 2 (ADM2).
4. Coordinates or grid cells.

Use WGS84 (EPSG:4326) for geographic coordinates unless a particular analytical workflow requires another projection.

---

## 3. Primary data sources

### 3.1 Malaria prevalence data

**Source:** Malaria Atlas Project (MAP)  
**Website:** https://malariaatlas.org/

Purpose:

- Historical malaria prevalence.
- Plasmodium falciparum prevalence (PfPR).
- Plasmodium vivax prevalence (PvPR), where available.
- Geographic malaria burden analysis.

Important variables:

- Survey coordinates.
- Survey year.
- Number examined.
- Number positive.
- Age range.
- Diagnostic method.
- Species.
- Source identifier.

Requirements:

- Preserve original survey metadata.
- Record the year of observation.
- Distinguish survey observations from modelled prevalence surfaces.
- Do not interpret missing observations as zero prevalence.

### 3.2 Environmental and weather data

**Source:** Open-Meteo  
**Website:** https://open-meteo.com/

Purpose:

- Temperature monitoring.
- Rainfall analysis.
- Relative humidity.
- Historical weather.
- Environmental context for malaria surveillance.

Potential variables:

- Temperature.
- Precipitation.
- Relative humidity.
- Daily and monthly summaries.

**Important:** Weather conditions are environmental covariates, not direct measurements of malaria prevalence.

Record the provider, retrieval date, coordinates, time period and data type.

**Current implementation note:** Open-Meteo integration has been tested in the backend. Its licensing and attribution requirements must be verified before final release.

### 3.3 Population data

**Source:** WorldPop  
**Website:** https://www.worldpop.org/

Purpose:

- Population distribution.
- Population density.
- Population potentially exposed to malaria.
- Geographic population analysis.

Potential variables:

- Population count.
- Population density.
- Geographic resolution.
- Reference year.
- Population estimates.

Population-at-risk calculations must clearly distinguish estimated population potentially exposed from confirmed malaria infections.

### 3.4 Administrative boundaries

Potential sources:

- GADM: https://gadm.org/
- Humanitarian Data Exchange: https://data.humdata.org/

Purpose:

- Country boundaries.
- Regional boundaries.
- District boundaries.
- Administrative mapping.

Requirements:

- Record the boundary version.
- Preserve administrative identifiers.
- Check geometry validity.
- Ensure country and region relationships are consistent.
- Verify licensing and redistribution conditions.

### 3.5 Health and socioeconomic indicators

**Source:** World Bank Open Data  
**Website:** https://data.worldbank.org/

Potential variables:

- Population indicators.
- Health expenditure.
- Socioeconomic indicators.
- Urbanization.
- Other contextual development indicators.

Use only indicators relevant to the project's analytical objectives.

### 3.6 Drug efficacy and resistance evidence

**Source:** World Health Organization (WHO)  
**Website:** https://www.who.int/

Purpose:

- Antimalarial treatment efficacy evidence.
- Drug resistance surveillance.
- Therapeutic efficacy studies.
- Validated resistance markers.

Potential indicators:

- Artemisinin-based combination therapy efficacy.
- PCR-corrected adequate clinical and parasitological response.
- Treatment follow-up duration.
- Resistance marker frequency.
- Study location and year.
- Sample size.
- Confidence intervals.

**Important:** A resistance marker frequency is not automatically equivalent to clinical treatment failure.

Drug efficacy evidence must retain study-level metadata and distinguish day-28 and day-42 outcomes.

---

## 4. Data classification

Every dataset must be classified into one of these categories:

**Observed data** - Measurements collected through surveys, laboratory studies, field observations or monitoring systems.

**Modelled data** - Estimates generated by statistical or machine learning models.

**Synthetic data** - Artificially generated records used for development, demonstrations or testing.

These categories must never be confused.

Frontend visualizations and AI responses must clearly communicate the category of information being displayed.

---

## 5. Data quality requirements

Before importing a dataset, check:

1. Source authenticity.
2. Data collection methodology.
3. Geographic coverage.
4. Reference year.
5. Missing values.
6. Duplicate records.
7. Coordinate validity.
8. Units and measurement definitions.
9. Licensing and attribution.
10. Reproducibility.

Do not silently replace missing values with zero.

Do not combine measurements with incompatible units or definitions.

Do not claim a dataset is validated without documenting the validation process.

---

## 6. Machine learning data requirements

The ML team should use the documented data sources and maintain traceability between input variables and model outputs.

Potential model inputs:

- Historical malaria prevalence.
- Temperature.
- Rainfall.
- Humidity.
- Population density.
- Elevation.
- Vegetation indicators.
- Geographic location.
- Relevant socioeconomic indicators.

Potential prediction target:

- Plasmodium falciparum parasite rate (PfPR).

Model evaluation should consider:

- MAE.
- RMSE.
- Spatial validation.
- Geographic generalization.
- Uncertainty estimates.
- Performance across countries and time periods.

A model must not be described as trained or validated until actual training and evaluation have been completed.

---

## 7. Backend integration requirements

The backend team must preserve:

- Dataset source identifiers.
- Geographic identifiers.
- Observation dates and reference years.
- Units.
- Data classifications.
- Provenance metadata.
- Data quality status.

Use consistent API response structures.

Missing data should return an explicit no-data response rather than a misleading zero.

The backend must distinguish:

- Observed prevalence.
- Modelled prevalence.
- Environmental measurements.
- Synthetic test records.

---

## 8. Frontend integration requirements

The frontend must:

- Display measurement units.
- Identify data sources.
- Show reference years.
- Distinguish observed and modelled values.
- Display uncertainty where available.
- Handle missing data correctly.
- Avoid presenting synthetic data as real surveillance evidence.

Maps and charts must communicate their geographic and temporal coverage.

---

## 9. AI assistant requirements

The AI assistant must use evidence available through approved backend services.

It must:

- Identify evidence sources.
- Reference evidence identifiers where available.
- Explain uncertainty.
- Avoid inventing statistics.
- Distinguish model predictions from observed measurements.
- State when information is unavailable.
- Avoid diagnosis and individual treatment recommendations.

AI-generated explanations must not be presented as independently verified scientific evidence.

---

## 10. Licensing and attribution

Every contributor introducing a new data source must document:

- Dataset name.
- Provider.
- Official source URL.
- License.
- Attribution requirements.
- Access or retrieval date.
- Any restrictions on redistribution or commercial use.

Publicly accessible does not automatically mean unrestricted for redistribution.

Sources with unverified licensing must remain flagged for verification.

---

## 11. Data storage and security

The project should use PostgreSQL with PostGIS for structured and geographic information.

Data management requirements:

- Preserve original source metadata.
- Maintain reproducible import processes.
- Keep raw data separate from processed datasets.
- Exclude sensitive credentials from Git.
- Avoid storing identifiable patient information.
- Use aggregated, anonymized or appropriately synthetic data.

Never commit:

- API keys.
- Database passwords.
- Private credentials.
- Personal health records.
- Restricted datasets.

---

## 12. Team responsibilities

| Team | Responsibility |
|---|---|
| Backend | Data models, validation, APIs and provenance |
| ML | Dataset preparation, features, training and evaluation |
| Frontend | Accurate presentation, maps, charts and uncertainty |
| AI | Evidence-grounded responses and source attribution |
| Architect | Data standards, integration and consistency |

---

## 13. Rules for introducing new datasets

Before adding a new dataset:

1. Identify the official provider.
2. Explain why the dataset is needed.
3. Verify its geographic and temporal coverage.
4. Check its licensing.
5. Document its variables and units.
6. Identify limitations.
7. Update this document.
8. Communicate the change to the team.

Do not independently introduce incompatible data structures.

---

## 14. Final project principle

MalariaWatchAI is an evidence-based malaria surveillance and geospatial analytics platform.

Our objective is not simply to display numbers or generate predictions.

We must ensure that every result is traceable to its source, scientifically interpretable, geographically relevant and transparent about uncertainty.

One project. One shared data reference. Consistent standards across every engineering team.

---

## 15. Datasets currently downloaded or used (section 13 register)

Maintained by the ML engineer for the data fetch layer (`python -m mal.fetch`) and the
ML pipeline (`python -m ml.src.pipeline`). All were retrieved on **2026-11-12** (exact
UTC times, URLs and SHA-256 checksums: [docs/DATA_MANIFEST.md](docs/DATA_MANIFEST.md)).
Raw files live in `data/raw/` and are not committed. No synthetic data is used in any
output; test fixtures in `ml/tests/` are labelled as such.

Licence status follows section 10: **open** (attribution required), **restricted**
(non-commercial terms - check before any redistribution or commercial use), **mixed**
(per-record or per-report terms), **ODbL** (share-alike for derived databases).

### 15.1 Datasets listed in sections 3.1-3.6 and how they are used

| Section | Dataset | Status in the project |
|---|---|---|
| 3.1 | MAP PfPR / PvPR surveys | **Used** - see 15.2 |
| 3.2 | Open-Meteo | Backend only (current/historical weather, `/environment/`). **Not a model input**: the prevalence model needs covariates for every survey year since 2000 at every location, so it uses WorldClim climatology (15.2). Licence to verify before release (section 3.2 note). |
| 3.3 | WorldPop | **Used** - see 15.2 |
| 3.4 | GADM / Humanitarian Data Exchange | **Not used.** geoBoundaries gbOpen is used instead (15.2): open licences (GADM forbids commercial redistribution), stable `shapeID` identifiers, and the backend's `import_boundaries` already reads `shapeID`. Proposed for team adoption. |
| 3.5 | World Bank Open Data | Not used. No indicator is needed by the current model; none has district-level coverage. |
| 3.6 | WHO efficacy and resistance evidence | **Used** - WHO Malaria Threats Map and WHO report (15.2) |

### 15.2 Register

| Dataset | Provider and URL | Coverage and period | Classification (s.4) | Licence (s.10) | Used for | Key limitations |
|---|---|---|---|---|---|---|
| PfPR survey points, release 202406 | Malaria Atlas Project - data.malariaatlas.org (WFS) | KEN, TZA, ETH (+UGA downloaded, out of scope); analysis window 2000-2024 (656 earlier records excluded) | Observed | CC BY 4.0; per-record permissions - **mixed** | Prevalence model target; observed prevalence | 6,249 of 9,469 records withheld by MAP; latest open survey KEN/TZA 2016; mixed ages and diagnostics |
| PvPR survey points, release 202406 | Malaria Atlas Project | As above | Observed | **mixed** | Species evidence (P. vivax) | 158 usable points |
| WorldClim 2.1 bioclim + elevation, 30 arc-s | WorldClim - worldclim.org | Per-country tiles; 1970-2000 | Modelled (interpolated climatology) | Free for academic/non-commercial use - **restricted** | Temperature, rainfall, seasonality, elevation covariates | Climatology, not 2020 weather; no humidity variable |
| MODIS MOD13A1 v061 NDVI, 2020 annual median | NASA via Microsoft Planetary Computer | Study bbox; 2020 | Observed (satellite, aggregated) | NASA EOSDIS open - **open** | Vegetation covariate | Single year applied to all survey years |
| WorldPop 2020 UN-adjusted, 1 km (counts + density) | WorldPop - worldpop.org | Per country; 2020 | Modelled (population model) | CC BY 4.0 - **open** | Population density covariate; population at risk | Modelled estimate, not a census |
| GHSL SMOD 2020, R2023A, 1 km | European Commission JRC - ghsl.jrc.ec.europa.eu | Global, clipped; 2020 | Modelled (settlement classification) | CC BY 4.0 - **open** | Urban/rural covariate | Single year applied to all survey years |
| HydroRIVERS v1.0 Africa | HydroSHEDS - hydrosheds.org | Africa; static | Modelled (from elevation data) | Free with attribution - **open** | Distance-to-water covariate (Strahler order >= 3) | Excludes small streams, seasonal pools, irrigation |
| Natural Earth 10 m lakes / rivers | naturalearthdata.com | Global; static | Observed (cartographic) | Public domain - **open** | Distance-to-water covariate (lakes) | Coarse scale |
| geoBoundaries gbOpen ADM0-ADM2 (commit 9469f09) | William & Mary geoLab - geoboundaries.org | KEN, TZA, ETH (+UGA) | Observed (administrative records) | Per layer: public domain, CC BY 3.0 IGO, CC BY 4.0, ODbL - **ODbL share-alike** for ETH ADM0/ADM2, TZA ADM1 | Region ids (`shapeID`), grid assignment, district outputs | ADM1 and ADM2 layers do not always nest |
| WHO Malaria Threats Map - therapeutic efficacy and molecular marker studies | WHO - apps.who.int/malaria/maps/threats (xMart public API) | KEN, TZA, ETH (+UGA); 2010-2023 for AL TES | Observed | CC BY-NC-SA 3.0 IGO - **restricted** | AL / DHA-PPQ / AS-AQ efficacy; pfkelch13 marker frequencies | Purposive sites; 69 of 161 K13 studies lack genotype detail; failure counts reconstructed from proportion x N |
| MalariaGEN Pf7 (samples, drug-resistance genotypes) | MalariaGEN - malariagen.net | KEN, TZA, ETH samples 1994-2018 | Observed | CC BY 4.0 - **open** | pfcrt K76T, pfmdr1 copy number, pfkelch13 | Few sites; located to ADM1 centroids |
| WHO Global Health Observatory malaria indicators | WHO - ghoapi.azureedge.net | Country-year | Observed (reported cases) | CC BY-NC-SA 3.0 IGO - **restricted** | Country-level Pf / Pv reported case shares | Depends on testing and reporting completeness |
| GBIF Plasmodium occurrences | GBIF - gbif.org | Country | Observed (presence-only) | Per record (CC0 / CC BY / CC BY-NC) - **mixed** | Species presence only | Never used for prevalence or shares |
| Kenya Malaria Indicator Survey 2020, Table 4.9 (hand-entered) | DNMP / KNBS / ICF - dhsprogram.com/pubs/pdf/MIS36/MIS36.pdf | Kenya national; 2020 | Observed | DHS Program terms per report - **mixed** | National P. malariae / P. ovale shares | National only; microscopy limits |
| WHO Report on antimalarial drug efficacy, resistance and response (2020) | WHO IRIS | Global | Observed (report) | CC BY-NC-SA 3.0 IGO - **restricted** | Validated pfkelch13 marker list (Table 4) | Later WHO lists may differ |
| WHO guidelines (2025), WHO resistance strategy for Africa (2022) | WHO IRIS | Global | Observed (guidance) | CC BY-NC-SA 3.0 IGO - **restricted** | Assistant guideline search (planned) | Not used by the ML pipeline |
| MAP Duffy-negativity phenotype frequency (2011) | Malaria Atlas Project | Study bbox | Modelled | CC BY 4.0 - **open** | Downloaded; not currently used | - |

### 15.3 Derived (ML) outputs

All ML outputs in `data/processed/` carry a `data_classification` column (`observed` or
`modelled`; species rows without evidence are null), `evidence_ids` that resolve in
`data/processed/evidence.parquet` (which also records each source's classification and
licence status), and a `generated_at` timestamp. Units, columns and methods are in
[ml/README.md](ml/README.md); assumptions in [ASSUMPTIONS.md](ASSUMPTIONS.md); model
details in [MODEL_CARD.md](MODEL_CARD.md).

### 15.4 Open items for the team (section 13, step 8)

1. Adopt geoBoundaries as the boundary source in place of GADM/HDX (section 3.4).
2. Before any public release, review the **restricted** sources (WorldClim, WHO Threats
   Map, WHO GHO, WHO reports) and the ODbL boundary layers for redistribution terms.
3. Verify Open-Meteo licensing and attribution (section 3.2 note).
4. Merge note: the backend branch (`feature/backend-data`) has its own `DATA.md`; it
   should be merged into this single reference.

> **Note (merge of `feature/backend-data`):** this is the backend engineer's original `DATA.md`, kept
> unchanged so nothing is lost. The team's central data reference is now [DATA.md](../DATA.md). Content
> here that is not yet in DATA.md (for example the 15 selected study areas) should be merged into it
> by the team (DATA.md section 13).

# MalariaWatchAI Data Documentation

## 1. Overview

MalariaWatchAI uses epidemiological, environmental, geographic and population datasets to support malaria surveillance and geospatial analysis.

The platform is designed to combine multiple data sources into a unified system for exploring malaria prevalence, environmental conditions, population exposure, parasite species, antimalarial drug efficacy and resistance evidence.

This document describes the intended data sources, data structures, validation requirements, licensing considerations and known limitations.

An important principle is that every dataset must be traceable to its original source.

## 2. Geographic Coverage

The initial project focuses on 15 selected study areas across three East African countries.

### Kenya

| Study area | Administrative level |
|---|---|
| Nairobi | County |
| Kisumu | County |
| Mombasa | County |
| Kilifi | County |
| Kakamega | County |

### Tanzania

| Study area | Administrative level |
|---|---|
| Dar es Salaam | Region |
| Mwanza | Region |
| Morogoro | Region |
| Kagera | Region |
| Mtwara | Region |

### Ethiopia

| Study area | Administrative level |
|---|---|
| Addis Ababa | First-level administrative area |
| Oromia | First-level region |
| Amhara | First-level region |
| Gambela | First-level region |
| Benishangul-Gumuz | First-level region |

Administrative levels must be preserved when integrating geographic datasets.

Region names alone should not be used as unique identifiers. Official administrative identifiers and validated geographic boundaries should be preferred.

## 3. Data Categories

The platform is designed to work with the following categories of data:

| Category | Purpose |
|---|---|
| Malaria prevalence | Estimate geographic malaria burden |
| Geographic boundaries | Support spatial analysis and mapping |
| Environmental data | Describe climatic and environmental conditions |
| Population data | Estimate population potentially exposed |
| Parasite species | Explore malaria parasite distribution |
| Drug efficacy | Summarize antimalarial treatment efficacy studies |
| Drug resistance | Explore molecular resistance evidence |
| Scientific evidence | Track data sources and research publications |

## 4. Malaria Prevalence Data

### Primary source

**Malaria Atlas Project (MAP)**

Website: https://malariaatlas.org/

MAP is a key potential source of malaria epidemiological survey information and spatial malaria datasets.

The platform intends to use Plasmodium falciparum prevalence (PfPR) as its primary prevalence target.

### Expected survey fields

| Field | Description |
|---|---|
| Survey ID | Unique survey identifier |
| Latitude | Survey latitude |
| Longitude | Survey longitude |
| Survey year | Year of data collection |
| Examined | Number of people examined |
| Positive | Number of positive individuals |
| Age range | Age group represented |
| Diagnostic method | Diagnostic method used |
| Source ID | Original evidence reference |

### Data preparation

The intended historical survey preparation period is 2000–2024, subject to data availability and validation.

Preferred age range for the initial analysis is 2–10 years where appropriate and sufficiently represented.

Survey observations should be checked for:

- Missing coordinates.
- Invalid sample counts.
- Duplicate records.
- Inconsistent survey dates.
- Diagnostic method differences.
- Geographic inconsistencies.
- Source and licensing information.

Observed survey prevalence must remain distinguishable from modelled prevalence estimates.

## 5. Geographic Boundary Data

Geographic boundaries are required for regional analysis, spatial filtering and map visualization.

Potential sources include:

- GADM: https://gadm.org/
- Humanitarian Data Exchange (HDX): https://data.humdata.org/
- Official national statistical and mapping authorities.

### Required geographic fields

| Field | Description |
|---|---|
| Geographic ID | Unique administrative identifier |
| Country code | ISO country identifier |
| Region name | Administrative area name |
| Administrative level | Geographic hierarchy level |
| Geometry | Polygon or multipolygon |
| Source | Boundary data provider |
| Reference year | Boundary reference period |

### Geographic validation

Before importing geographic data:

1. Confirm the country.
2. Confirm the administrative level.
3. Check geographic identifiers.
4. Validate polygon geometry.
5. Check coordinate reference systems.
6. Identify duplicate or overlapping records.
7. Record source and licensing details.

PostGIS is used to support geographic storage and spatial queries.

Boundary datasets must not be combined solely because their administrative area names look similar.

## 6. Environmental Data

### Primary integration

**Open-Meteo**

Website: https://open-meteo.com/

Open-Meteo provides access to weather and historical climate information.

The platform uses environmental information to provide additional context for malaria surveillance.

### Expected environmental variables

| Variable | Unit |
|---|---|
| Temperature | Degrees Celsius |
| Relative humidity | Percentage |
| Precipitation | Millimetres |
| Wind speed | Kilometres per hour |
| Observation or model timestamp | UTC timestamp |

Historical weather information may support retrospective analysis, while current weather provides an indication of present environmental conditions.

### Important limitations

- Provider-derived weather values are not necessarily direct weather station observations.
- Environmental conditions do not independently establish malaria transmission.
- Current weather must not be substituted for historical model covariates without justification.
- Weather and malaria prevalence may have different spatial and temporal resolutions.

The Open-Meteo evidence record is identified in the current project as `E900`.

Its licence and attribution verification must be completed before the evidence source is considered fully validated.

## 7. Population Data

Population information is intended to support estimates of population potentially exposed to malaria.

Potential sources include:

- WorldPop: https://www.worldpop.org/
- World Bank: https://data.worldbank.org/
- National census and statistical authorities.

### Expected fields

| Field | Description |
|---|---|
| Geographic ID | Administrative identifier |
| Population count | Estimated population |
| Reference year | Population reference period |
| Geographic resolution | Spatial resolution |
| Source ID | Original source reference |

### Population at risk calculation

A simplified estimate is:

\[
Population\ potentially\ exposed =
Estimated\ prevalence \times Population
\]

The calculation requires compatible geographic areas and reference periods.

Population potentially exposed is not the same as the number of confirmed malaria infections.

Population estimates must not be presented as patient or confirmed case counts.

## 8. Parasite Species Data

The platform is designed to support evidence relating to:

- Plasmodium falciparum.
- Plasmodium vivax.
- Plasmodium malariae.
- Plasmodium ovale.
- Plasmodium knowlesi.

Potential sources include peer-reviewed scientific publications and validated surveillance datasets.

Species records should include:

- Species name.
- Geographic location.
- Observation date.
- Diagnostic method.
- Number of tested samples, where available.
- Source identifier.
- Evidence quality.

Presence-only observations must not be interpreted as species-specific case proportions.

Species distribution modelling requires sufficient representative observations and appropriate validation.

## 9. Drug Efficacy Data

The platform is intended to organize evidence concerning antimalarial medicines.

Initial treatment categories include:

| Medicine | Abbreviation |
|---|---|
| Artemether-lumefantrine | AL |
| Dihydroartemisinin-piperaquine | DHA-PPQ |
| Artesunate-amodiaquine | ASAQ |

Potential evidence sources include:

- World Health Organization publications.
- Published therapeutic efficacy studies.
- Peer-reviewed research articles.
- Validated national surveillance reports.

### Expected fields

| Field | Description |
|---|---|
| Study ID | Unique study identifier |
| Medicine | Treatment evaluated |
| Country | Study country |
| Region | Study location |
| Study year | Year of study |
| Sample size | Number of participants |
| ACPR | Adequate clinical and parasitological response |
| Follow-up period | Day 28 or day 42 |
| PCR correction | Whether PCR correction was applied |
| Source ID | Evidence reference |

Results from different follow-up periods and methodologies must not be combined without appropriate statistical justification.

Drug efficacy summaries are intended for research and surveillance, not individual treatment recommendations.

## 10. Drug Resistance Data

The platform may include molecular resistance evidence involving:

- pfkelch13.
- pfmdr1.
- pfcrt.

Potential sources include:

- WHO malaria reports.
- Peer-reviewed molecular surveillance studies.
- Validated national research datasets.

### Expected fields

| Field | Description |
|---|---|
| Study ID | Unique study identifier |
| Marker | Genetic marker |
| Mutation | Specific mutation |
| Tested samples | Number tested |
| Mutant samples | Number with mutation |
| Frequency | Observed mutation frequency |
| Country | Country of study |
| Region | Geographic location |
| Study year | Collection year |
| Source ID | Evidence reference |

Mutation frequency must not automatically be interpreted as clinical treatment failure.

Results should include sample sizes, study dates and uncertainty where available.

## 11. Evidence Management and Data Provenance

The backend includes an evidence management component.

Evidence identifiers connect scientific records to their original sources.

Each evidence source should ideally include:

| Field | Description |
|---|---|
| Evidence ID | Unique evidence identifier |
| Source name | Name of publisher or provider |
| Source URL | Original source location |
| Data category | Type of evidence |
| Publication date | Publication date |
| Access date | Retrieval date |
| Licence | Applicable licence |
| Attribution | Required acknowledgement |
| Validation status | Evidence review status |

### Evidence status

Evidence should be classified according to its validation state.

Suggested statuses:

- `PENDING_REVIEW`
- `VALIDATED`
- `REJECTED`
- `VERIFY_LICENSE`
- `SYNTHETIC`

The exact values should follow the actual backend implementation.

An evidence record should not be marked validated until its source, quality and licensing conditions have been reviewed.

## 12. Data Quality and Validation

All incoming datasets should undergo validation before being used for scientific analysis.

### General validation checks

- Source authenticity.
- File integrity.
- Geographic coordinate validity.
- Missing values.
- Duplicate records.
- Data type consistency.
- Reference period consistency.
- Geographic identifier matching.
- Licensing and attribution.
- Scientific relevance.

### Scientific validation

Additional checks depend on the dataset category.

For prevalence data:

- Positive sample count must not exceed examined sample count.
- Survey location must be valid.
- Survey year must be recorded.
- Diagnostic method must be documented.

For environmental data:

- Units must be consistent.
- Timestamps must be recorded.
- Missing observations must be identified.
- Provider information must be retained.

For population data:

- Geographic coverage must be verified.
- Reference year must be recorded.
- Spatial resolution must be documented.

## 13. Data Classification

MalariaWatchAI distinguishes three important data classes.

### Observed data

Information obtained from actual surveys, studies, measurements or validated surveillance sources.

### Modelled data

Information generated by statistical or machine learning methods using available input data.

### Synthetic data

Artificially generated information used for software development, demonstrations or testing.

These categories must remain distinguishable throughout the system.

Synthetic data must never be presented as observed malaria evidence.

Modelled outputs must include relevant model and uncertainty information.

## 14. Data Licensing and Attribution

Every external dataset must be reviewed for its applicable licence and usage requirements.

Contributors must verify:

- Commercial and non-commercial usage permissions.
- Redistribution conditions.
- Attribution requirements.
- Derivative data restrictions.
- API usage restrictions.
- Geographic data licensing conditions.

The presence of a publicly accessible download or API does not automatically mean unrestricted reuse is permitted.

Relevant provider terms should be reviewed before data is incorporated into a public release.

## 15. Current Data Availability

The following table records the current known status of the project based on backend checks performed during development.

| Dataset or component | Current status |
|---|---|
| Country records | Available for Kenya, Tanzania and Ethiopia |
| Administrative regions | No validated records returned in the tested API response |
| Prevalence observations | No validated records returned in the tested API response |
| Prevalence map features | No features returned in the tested API response |
| Drug efficacy | No validated records returned in the tested API response |
| Resistance evidence | No validated records returned in the tested API response |
| Current environmental service | Successfully tested with Open-Meteo |
| Historical environmental service | Successfully tested with Open-Meteo |
| Open-Meteo evidence licence | Verification pending for E900 |
| Synthetic evidence | E001 identified as a synthetic record |

These statuses reflect the recorded development checks, not a guarantee of the database's current state.

An empty API response indicates that validated records were unavailable for that query. It does not establish zero prevalence, zero resistance or absence of malaria.

## 16. Data Storage and Integration

The backend uses:

- PostgreSQL for relational data storage.
- PostGIS for spatial data management.
- Django models for application data structures.
- Django REST Framework for API access.

The frontend is designed to consume backend data through versioned REST endpoints.

Geographic information can be returned in GeoJSON format for visualization using MapLibre GL JS.

## 17. Data Security and Privacy

The project prioritizes public, aggregated, anonymized and synthetic data.

The following principles apply:

- Do not commit API keys or credentials.
- Do not upload patient-identifiable information.
- Do not expose confidential surveillance records.
- Respect data provider access conditions.
- Restrict access to administrative operations.
- Preserve source attribution.
- Use secure environment configuration.

## 18. Known Data Limitations

The current project has several data-related limitations:

1. Not all selected administrative areas have validated geographic records.
2. Prevalence datasets have not yet been confirmed as populated in the tested API responses.
3. Drug efficacy and resistance records are not yet available in the tested API responses.
4. Species-specific evidence may be incomplete.
5. Population datasets require geographic and temporal validation.
6. Environmental information is not direct evidence of malaria prevalence.
7. External data licensing must be verified before redistribution.
8. Model training depends on validated and sufficiently representative datasets.

These limitations must be updated as new data is imported and validated.

## 19. Future Data Improvements

Planned improvements include:

- Importing validated administrative boundaries.
- Acquiring and validating malaria prevalence survey records.
- Integrating population datasets.
- Expanding environmental covariates.
- Adding validated parasite species evidence.
- Integrating therapeutic efficacy studies.
- Integrating molecular resistance evidence.
- Maintaining a complete evidence registry.
- Automating data quality checks.
- Improving temporal and geographic consistency.

## 20. References and External Resources

- Malaria Atlas Project: https://malariaatlas.org/
- Open-Meteo: https://open-meteo.com/
- WorldPop: https://www.worldpop.org/
- World Bank Data: https://data.worldbank.org/
- GADM: https://gadm.org/
- Humanitarian Data Exchange: https://data.humdata.org/
- World Health Organization: https://www.who.int/

All sources must be reviewed individually for relevance, publication date, methodology and licensing.

---

**Project:** MalariaWatchAI

**Document:** Data Documentation

**Version:** 1.0

**Status:** Development documentation

**Last updated:** 13 November 2026
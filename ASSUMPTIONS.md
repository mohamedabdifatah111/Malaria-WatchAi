# MalariaWatchAI Assumptions and Limitations

## 1. Purpose

This document records the assumptions, scientific considerations, technical constraints and limitations guiding the development of MalariaWatchAI.

The purpose is to ensure that system outputs are interpreted responsibly and that users understand the difference between observed evidence, modelled estimates and unavailable information.

These assumptions should be reviewed whenever new datasets, models or system capabilities are introduced.

## 2. Geographic Scope

MalariaWatchAI initially focuses on selected administrative areas in three East African countries:

- Kenya
- Tanzania
- Ethiopia

The planned study areas are:

### Kenya
- Nairobi
- Kisumu
- Mombasa
- Kilifi
- Kakamega

### Tanzania
- Dar es Salaam
- Mwanza
- Morogoro
- Kagera
- Mtwara

### Ethiopia
- Addis Ababa
- Oromia
- Amhara
- Gambela
- Benishangul-Gumuz

**Assumptions:**

- Geographic boundaries will be obtained from reliable sources.
- Administrative identifiers will be used to match geographic records.
- Administrative levels will remain consistent with the source datasets.
- Geographic boundaries may change over time and must be versioned where necessary.
- The selected study areas do not represent complete national coverage.

## 3. Malaria Prevalence

The platform is designed to support the analysis of Plasmodium falciparum prevalence, commonly represented as PfPR.

**Assumptions:**

- Malaria survey records are the primary source of empirical prevalence evidence.
- Survey year, location, diagnostic method, age range and sample size influence interpretation.
- Surveys with different age groups or diagnostic methods may not be directly comparable.
- Historical survey observations do not automatically represent current malaria prevalence.
- Spatial estimates require appropriate geographic and temporal validation.

The intended reference period for the initial prevalence analysis is 2020, subject to data availability and model validation.

### Limitations

- Survey coverage may be uneven.
- Some regions may have limited observations.
- Estimates between survey locations involve uncertainty.
- Extrapolation beyond the geographic coverage of available evidence may be unreliable.

An empty dataset must never be interpreted as zero malaria prevalence.

## 4. Environmental Variables

Environmental information may help explain geographic and seasonal variation in malaria transmission.

Potential explanatory variables include:

- Temperature.
- Rainfall.
- Relative humidity.
- Vegetation indices.
- Elevation.
- Distance to water bodies.
- Population density.
- Urban and rural classification.

**Assumptions:**

- Environmental conditions can contribute to malaria transmission suitability.
- Environmental relationships may differ between geographic areas.
- Historical environmental conditions are more appropriate for historical prevalence modelling than unrelated current weather readings.
- Environmental variables alone cannot establish malaria prevalence or disease occurrence.

Open-Meteo data may provide supporting environmental information.

Provider-derived or model-based weather conditions must not automatically be treated as direct weather station observations.

## 5. Population at Risk

The platform may estimate population exposure using malaria prevalence estimates and population datasets.

A simplified calculation is:

Population potentially exposed = Estimated prevalence × Population count

**Assumptions:**

- Population datasets represent the relevant geographic area and reference period.
- Prevalence estimates and population counts are geographically compatible.
- Both inputs are sufficiently reliable for the intended calculation.

### Important distinction

Population potentially exposed does not mean the number of confirmed malaria infections.

The estimate should not be presented as a count of infected individuals, diagnosed patients or confirmed cases.

## 6. Parasite Species

The platform is intended to support exploration of malaria parasite species, including:

- Plasmodium falciparum.
- Plasmodium vivax.
- Plasmodium malariae.
- Plasmodium ovale.
- Plasmodium knowlesi.

**Assumptions:**

- Species records must be supported by reliable diagnostic or surveillance evidence.
- Species presence does not establish the proportion of malaria cases caused by that species.
- Species distribution models require sufficient geographically representative observations.
- Species-specific conclusions must reflect the limitations of available evidence.

Presence-only observations should not be used to calculate case proportions without appropriate denominator data.

## 7. Antimalarial Drug Efficacy

The platform may organize evidence concerning antimalarial medicines, including:

- Artemether-lumefantrine (AL).
- Dihydroartemisinin-piperaquine (DHA-PPQ).
- Artesunate-amodiaquine (ASAQ).

**Assumptions:**

- Published therapeutic efficacy studies are the primary evidence source.
- PCR-corrected adequate clinical and parasitological response (ACPR) should be distinguished from uncorrected outcomes.
- Follow-up periods, such as day 28 and day 42, must be reported separately.
- Study populations, locations and methodologies may differ.
- Pooled estimates require appropriate statistical methods.

Study-level results must not automatically be generalized to every location or population.

Drug efficacy summaries are intended for research and surveillance, not individual treatment recommendations.

## 8. Antimalarial Resistance

The platform may support analysis of molecular resistance markers, including:

- pfkelch13.
- pfmdr1.
- pfcrt.

**Assumptions:**

- Resistance findings must be linked to validated molecular evidence.
- Mutation frequencies depend on the number and characteristics of tested samples.
- Different mutations may have different scientific and clinical significance.
- Marker frequency alone does not establish clinical treatment failure.

Resistance summaries should include tested sample counts, mutation counts, study dates, geographic coverage and uncertainty where available.

A single study should not be treated as definitive evidence of a regional trend.

## 9. Geospatial Modelling

The platform is designed to support spatial prediction using malaria survey observations and environmental covariates.

Potential modelling approaches include:

- Gradient boosting methods.
- LightGBM.
- Inverse Distance Weighting.
- Regional mean baselines.
- Quantile-based uncertainty estimation.

**Assumptions:**

- Training observations are sufficiently representative of the prediction area.
- Geographic and temporal differences influence model performance.
- Spatially independent validation is preferable to relying only on random train-test splits.
- Model performance must be compared against appropriate baseline methods.

### Model evaluation

Potential evaluation metrics include:

- Mean Absolute Error (MAE).
- Root Mean Squared Error (RMSE).
- Spearman correlation.
- Prediction interval coverage.

Spatial validation may use geographic blocks and leave-one-administrative-region-out evaluation.

### Limitations

- Sparse survey data can reduce predictive reliability.
- Environmental covariates may not capture all transmission drivers.
- Predictions outside observed geographic coverage involve extrapolation.
- Model uncertainty should be communicated alongside estimates.

No model should be described as trained, validated or production-ready until the corresponding processes have been completed and documented.

## 10. AI Assistant

MalariaWatchAI is designed to use Google's Gemini API for AI-assisted information exploration.

**Assumptions:**

- AI responses should be grounded in available platform evidence.
- The assistant should identify supporting evidence where possible.
- Missing evidence must be communicated clearly.
- AI-generated explanations may contain errors and require verification.
- The assistant is not a substitute for epidemiologists, clinicians or public health authorities.

The assistant must not:

- Diagnose individual patients.
- Prescribe medicines or dosages.
- Invent scientific evidence.
- Present uncertain estimates as confirmed facts.
- Treat weather conditions as proof of malaria transmission.

Important public health conclusions should remain subject to human review.

## 11. Data Quality and Provenance

All scientific datasets should have traceable sources.

**Assumptions:**

- Data sources can differ in collection methods and reliability.
- Missing values are not equivalent to zero.
- Records may require cleaning and validation before analysis.
- Geographic identifiers should be checked before spatial integration.
- Data licences and attribution conditions must be respected.

Each important dataset should record:

- Source name.
- Source identifier.
- Collection or publication date.
- Geographic coverage.
- Reference period.
- Methodology.
- Licence information.
- Validation status.

Synthetic records must always be labelled as synthetic and must never be presented as real epidemiological observations.

## 12. Temporal Consistency

Malaria prevalence, environmental conditions and population datasets may refer to different years.

**Assumptions:**

- Reference periods must be recorded explicitly.
- Historical estimates should use appropriately matched historical covariates.
- Current environmental conditions must not be substituted for historical conditions without justification.
- Population estimates should correspond as closely as possible to the relevant prevalence reference period.

Temporal mismatches should be documented as limitations.

## 13. Missing Data

The system may encounter incomplete geographic, environmental or epidemiological records.

**Assumptions:**

- Missing data must remain distinguishable from zero.
- Unavailable datasets should produce explicit no-data responses.
- Missing values should not be silently replaced with invented observations.
- Any imputation method must be documented.
- Data availability should be communicated to users.

## 14. System and Infrastructure

The backend uses Django REST Framework and PostgreSQL with PostGIS.

The frontend is designed around React, TypeScript and MapLibre GL JS.

**Assumptions:**

- API responses provide the primary communication mechanism between frontend and backend.
- External services may experience downtime or rate limits.
- API credentials must be managed securely.
- Spatial functionality depends on correctly configured geographic libraries and database extensions.
- Production deployment requires additional security, monitoring and performance configuration.

## 15. Ethical and Responsible Use

MalariaWatchAI is intended to support research, surveillance and evidence exploration.

The platform should:

- Avoid exposing patient-identifiable information.
- Communicate uncertainty and limitations.
- Avoid stigmatizing geographic communities.
- Avoid unsupported public health conclusions.
- Respect data ownership and licensing requirements.
- Encourage consultation with qualified public health professionals.

The platform does not replace official malaria surveillance systems or clinical decision-making.

## 16. Known Project Limitations

The following limitations must be considered during development and demonstration:

1. Some geographic areas may not yet have validated boundary data.
2. Malaria prevalence datasets may be incomplete or unavailable.
3. Drug efficacy and resistance evidence may have uneven geographic coverage.
4. Species-specific records may be insufficient for reliable distribution modelling.
5. Environmental data does not independently establish malaria transmission.
6. Population exposure estimates depend on the quality and compatibility of their input datasets.
7. AI-generated explanations require evidence grounding and human verification.
8. Spatial model accuracy depends on the availability and quality of training data.

These limitations should be updated as the project progresses.

## 17. Review and Updates

This document should be reviewed whenever:

- New datasets are introduced.
- Scientific methods change.
- Geographic coverage expands.
- Model assumptions are revised.
- AI capabilities change.
- Important data quality issues are discovered.

All changes should be documented to maintain transparency and reproducibility.

---

**Document status:** Development assumptions and limitations.

**Project:** MalariaWatchAI

**Purpose:** Scientific transparency, responsible development and reproducibility.
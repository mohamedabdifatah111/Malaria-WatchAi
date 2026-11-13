# MalariaWatchAI Model Card

## 1. Model Overview

**Project:** MalariaWatchAI

**Model name:** Malaria Prevalence Prediction Model

**Model type:** Geospatial machine learning model

**Primary target:** Plasmodium falciparum parasite rate (PfPR)

**Intended reference period:** 2020

**Geographic scope:** Selected study areas in Kenya, Tanzania and Ethiopia.

**Development status:** Research and development. Model training and validation results must be added after the corresponding experiments have been completed.

## 2. Model Purpose

The MalariaWatchAI model is designed to estimate geographic variation in malaria prevalence using epidemiological observations and environmental and geographic information.

Its intended purpose is to:

- Support geographic exploration of malaria prevalence.
- Identify areas that may require further surveillance.
- Help researchers understand spatial patterns.
- Support evidence-based public health planning.
- Provide geographic estimates alongside uncertainty information.

The model is intended as a research and surveillance support tool.

It is not designed to diagnose individual patients or determine individual treatment.

## 3. Intended Users

Potential users include:

- Public health researchers.
- Epidemiologists.
- Malaria surveillance teams.
- Public health institutions.
- Geographic information system (GIS) analysts.
- Academic researchers.
- Public health planning organizations.

## 4. Geographic Coverage

The initial target geography consists of 15 selected study areas.

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

These locations represent the intended study scope, not confirmation that validated training data is available for every area.

Administrative boundaries and identifiers must be validated before spatial modelling.

## 5. Prediction Target

The primary prediction target is Plasmodium falciparum prevalence.

PfPR represents the proportion of the relevant surveyed population testing positive for P. falciparum.

Where survey counts are available, empirical prevalence can be calculated as:

\[
PfPR = \frac{\text{Number of positive individuals}}
{\text{Number of individuals examined}}
\]

The survey population, age range, diagnostic method and collection year must accompany each observation.

Survey prevalence is an observed measurement. Modelled prevalence is an estimate and must be labelled separately.

## 6. Training Data

The intended primary training data consists of malaria prevalence survey records.

Potential data sources include:

- Malaria Atlas Project (MAP).
- Published malaria epidemiological studies.
- Validated national malaria surveillance datasets, where access and licensing permit.

### Required survey fields

| Field | Description |
|---|---|
| Survey ID | Unique observation identifier |
| Latitude | Geographic latitude |
| Longitude | Geographic longitude |
| Survey year | Year of data collection |
| Examined | Number of individuals examined |
| Positive | Number of positive individuals |
| Age range | Age group represented |
| Diagnostic method | Diagnostic approach |
| Source ID | Original evidence reference |

The intended historical data preparation period is 2000–2024, subject to source availability and validation.

Surveys targeting children aged 2–10 years are preferred for the initial analysis, where appropriate and sufficiently represented.

Records from different age groups and diagnostic methods must not be treated as automatically interchangeable.

## 7. Environmental and Geographic Features

Potential explanatory variables include:

| Feature | Purpose |
|---|---|
| Rainfall | Environmental transmission context |
| Temperature | Environmental suitability |
| Relative humidity | Environmental context |
| NDVI | Vegetation conditions |
| Elevation | Geographic and climatic variation |
| Distance to water | Geographic context |
| Population density | Human population distribution |
| Urban/rural classification | Settlement characteristics |

Feature selection will depend on data availability, temporal consistency and quality.

Environmental variables should correspond as closely as possible to the reference period of the prevalence observations.

Current weather conditions must not be substituted for historical covariates without scientific justification.

## 8. Data Preparation

The intended preprocessing workflow includes:

1. Checking source provenance and licensing.
2. Removing duplicate survey records.
3. Validating geographic coordinates.
4. Checking survey dates and reference periods.
5. Validating examined and positive sample counts.
6. Checking missing values.
7. Identifying inconsistent diagnostic methods.
8. Matching survey records with environmental features.
9. Matching geographic observations with validated administrative boundaries.
10. Preparing model-ready datasets.

Records with impossible sample counts or invalid coordinates should be rejected or investigated.

Synthetic records must not be used as real epidemiological training observations.

## 9. Model Methodology

The intended primary approach is gradient-boosted decision tree modelling.

LightGBM is a candidate implementation because it can model nonlinear relationships between environmental, geographic and epidemiological variables.

### Candidate baseline methods

The model will be compared with:

- Regional mean prevalence.
- Inverse Distance Weighting (IDW).
- Other appropriate simple statistical baselines.

### Spatial interpolation baseline

The planned IDW configuration is:

- Power parameter: 2.
- Nearest training observations: 12.

These parameters are initial experimental choices and should be reviewed during model evaluation.

### Model selection

The final model should be selected based on:

- Predictive performance.
- Spatial generalization.
- Stability across geographic areas.
- Data quality.
- Interpretability.
- Uncertainty characterization.

No model should be declared superior without experimental results.

## 10. Training and Validation Strategy

Random train-test splitting alone may overestimate model performance because nearby survey locations can have similar environmental and epidemiological characteristics.

The intended validation strategy therefore emphasizes spatial separation.

### Proposed validation methods

**Spatial block cross-validation**

- Divide the study geography into approximately 100 km × 100 km spatial blocks.
- Use GroupKFold with five folds.
- Keep observations from the same spatial block together.

**Leave-one-administrative-region-out validation**

- Hold out one administrative region.
- Train using observations from other regions.
- Evaluate the model on the held-out region.

This helps assess geographic generalization.

### Evaluation metrics

| Metric | Purpose |
|---|---|
| MAE | Average absolute prediction error |
| RMSE | Penalizes larger prediction errors |
| Spearman correlation | Measures agreement in geographic ranking |
| Interval coverage | Measures uncertainty interval reliability |

Results should be reported by country, reference period and prevalence range where sufficient observations exist.

## 11. Uncertainty Estimation

Malaria prevalence estimates should communicate uncertainty rather than presenting predictions as exact values.

The proposed approach includes:

- Quantile regression.
- Lower, median and upper prediction estimates.
- Conformalized quantile regression where feasible.
- Spatial block bootstrap experiments.

The intended prediction quantiles are:

- 5th percentile.
- 50th percentile.
- 95th percentile.

These may be used to construct an approximate 90% prediction interval.

A target of 90% interval coverage is an evaluation objective, not a verified result.

Uncertainty intervals must be evaluated using held-out spatial data.

## 12. Model Output

The intended model output includes:

| Output | Description |
|---|---|
| Geographic location | Prediction coordinates or geographic unit |
| Predicted PfPR | Estimated prevalence |
| Lower uncertainty bound | Lower prediction estimate |
| Median estimate | Central prediction estimate |
| Upper uncertainty bound | Upper prediction estimate |
| Reference period | Period represented by the estimate |
| Model version | Version of the prediction model |
| Evidence references | Supporting data sources |
| Data status | Observed, modelled or unavailable |

Outputs should be available in a format suitable for geographic visualization.

## 13. Limitations

The model may face the following limitations:

- Uneven malaria survey distribution.
- Limited observations in some geographic areas.
- Differences in survey diagnostic methods.
- Temporal mismatch between survey and environmental data.
- Incomplete geographic boundaries.
- Environmental variables that do not capture all transmission factors.
- Uncertainty in extrapolated areas.
- Changes in malaria transmission patterns over time.

Predictions outside well-supported training areas should be clearly flagged.

The model must not imply that a location has zero malaria risk simply because no survey observations are available.

## 14. Bias and Fairness Considerations

Survey data may be more available in some regions than others.

This can produce geographic bias and uneven prediction quality.

To reduce this risk:

- Examine survey distribution before training.
- Report performance separately by country and region.
- Identify areas with limited observations.
- Avoid interpreting poor data coverage as low malaria prevalence.
- Communicate model uncertainty.
- Avoid unsupported comparisons between regions.

The model should not be used to allocate healthcare resources automatically without appropriate public health review.

## 15. Responsible Use

The model is intended for:

- Research.
- Geographic surveillance.
- Public health evidence exploration.
- Preliminary identification of areas for further investigation.

It is not intended for:

- Individual diagnosis.
- Patient-level clinical decisions.
- Drug prescriptions.
- Treatment selection.
- Replacing official surveillance systems.
- Making unsupported claims about malaria absence or elimination.

All important public health interpretations should involve qualified professionals.

## 16. Performance and Reproducibility

The following information must be recorded after model development:

| Item | Status |
|---|---|
| Training dataset version | Pending |
| Training observation count | Pending |
| Feature list | Pending validation |
| Model algorithm | Planned: LightGBM |
| Model hyperparameters | Pending |
| Spatial validation results | Pending |
| MAE | Pending |
| RMSE | Pending |
| Spearman correlation | Pending |
| Prediction interval coverage | Pending |
| Model artifact version | Pending |

Training scripts, preprocessing steps, evaluation outputs and model configuration should be version-controlled.

Random seeds and software dependencies should be recorded to improve reproducibility.

## 17. Deployment Considerations

The intended deployment architecture integrates the model with the MalariaWatchAI backend.

The expected workflow is:

1. Scientific and environmental data are prepared.
2. A validated model is trained.
3. Evaluation results are reviewed.
4. The model artifact is versioned.
5. Backend services load the approved model.
6. Prediction outputs are exposed through API endpoints.
7. The frontend displays geographic estimates and uncertainty.
8. Model metadata and evidence references remain accessible.

Deployment should only occur after appropriate validation.

## 18. Future Improvements

Potential future improvements include:

- Expanding validated survey coverage.
- Adding more environmental covariates.
- Improving spatial validation.
- Evaluating alternative machine learning algorithms.
- Improving prediction interval calibration.
- Adding temporal modelling.
- Supporting additional malaria species where sufficient evidence exists.
- Evaluating performance across different countries and administrative levels.

## 19. Model Status and Disclaimer

**Current status:** Model development and validation are pending.

The methodology described in this document represents the planned modelling approach. It does not establish that a trained model, validated predictions or measured performance results currently exist.

All future model results must be supported by reproducible experiments and documented evaluation.

MalariaWatchAI is a research and surveillance support platform and is not a substitute for professional medical advice or official public health guidance.

---

**Project:** MalariaWatchAI

**Document:** Model Card

**Version:** 1.0

**Last updated:** 13 November 2026
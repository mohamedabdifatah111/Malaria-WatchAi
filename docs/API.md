# Malaria WatchAI
## API Contract and Integration Specification

**Version:** 1.0  
**Status:** Initial Engineering Specification  
**Project:** Malaria WatchAI  
**Geographic scope:** Kenya, Tanzania and Ethiopia  
**Backend:** Django REST Framework  
**Frontend:** React + Tailwind CSS  
**Database:** PostgreSQL + PostGIS  
**Data format:** JSON  
**API prefix:** `/api/v1/`

---

# 1. Purpose

This document defines the API contracts between the Malaria WatchAI frontend, backend, machine learning pipeline and evidence-grounded AI assistant.

All engineers must follow these contracts when implementing their respective components.

The objective is to ensure independent components can integrate without changing response structures unexpectedly.

# 2. System Architecture

The system has four main components:

1. React frontend: dashboard, maps, charts and user interactions.
2. Django REST API: data access, validation, application services and agent orchestration.
3. ML pipeline: prevalence predictions, uncertainty, species analysis, efficacy and resistance analysis.
4. PostgreSQL/PostGIS: geographic and structured data storage.

External data providers include MAP, WHO, MalariaGEN, WorldClim, MODIS, WorldPop and Open-Meteo.

The frontend must communicate with the backend through the REST API. It must not access the database directly.

# 3. General API Standards

## Base URL

Development:

`http://localhost:8000/api/v1/`

Production:

`https://YOUR_DOMAIN/api/v1/`

## HTTP Methods

- GET: Retrieve information.
- POST: Submit a request or create a resource.
- PATCH: Partially update a resource.
- DELETE: Delete a resource where permitted.

## Response format

All responses use JSON.

## Country identifiers

| Country | ISO code |
|---|---|
| Kenya | KEN |
| Tanzania | TZA |
| Ethiopia | ETH |

## Geographic identifiers

Use stable administrative boundary identifiers, not district names alone.

Every geographic record should identify its country and administrative level.

## Standard success response

```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2026-11-12T09:00:00Z",
    "source": "malaria-watchai"
  }
}
```

## Standard error response

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested geographic area was not found."
  }
}
```

## Common status codes

| Code | Meaning |
|---|---|
| 200 | Successful request |
| 201 | Resource created |
| 400 | Invalid request |
| 401 | Authentication required |
| 403 | Permission denied |
| 404 | Resource not found |
| 422 | Valid JSON but invalid domain data |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

# 4. API Endpoint Specifications

## 4.1 Geography API

**Owner:** Backend Engineer

### GET `/countries/`

Returns supported countries.

Example response:

```json
{
  "success": true,
  "data": [
    {
      "code": "KEN",
      "name": "Kenya"
    },
    {
      "code": "TZA",
      "name": "Tanzania"
    },
    {
      "code": "ETH",
      "name": "Ethiopia"
    }
  ]
}
```

### GET `/regions/?country=KEN&level=ADM2`

Returns geographic administrative areas.

Query parameters:

- `country`: KEN, TZA or ETH.
- `level`: ADM1 or ADM2.
- `search`: Optional geographic name.

Response fields:

- `id`
- `name`
- `country_code`
- `admin_level`
- `parent_id`
- `boundary`

The boundary should use GeoJSON geometry.

---

## 4.2 Prevalence API

**Owners:** ML Engineer and Backend Engineer

### GET `/prevalence/`

Returns prevalence estimates for a selected location.

Query parameters:

- `country`
- `region_id`
- `year`
- `source_type`: observed or modelled

Example:

`GET /prevalence/?country=KEN&year=2020`

Response:

```json
{
  "success": true,
  "data": [
    {
      "country": "KEN",
      "region_id": "REGION_ID",
      "region_name": "Example region",
      "year": 2020,
      "indicator": "PfPR",
      "estimate": null,
      "lower_interval": null,
      "upper_interval": null,
      "source_type": "modelled",
      "model_version": null,
      "evidence_ids": [],
      "status": "pending_data"
    }
  ]
}
```

The null values are placeholders until validated ML outputs are available.

### GET `/prevalence/map/`

Returns map-ready prevalence data.

Query parameters:

- `country`
- `year`
- `resolution`
- `indicator`

Response fields:

- `feature_id`
- `geometry`
- `estimate`
- `lower_interval`
- `upper_interval`
- `source_type`
- `model_version`
- `evidence_ids`

Geometry must be valid GeoJSON.

### GET `/prevalence/uncertainty/`

Returns uncertainty information.

Response fields:

- `region_id`
- `estimate`
- `lower_interval`
- `upper_interval`
- `interval_width`
- `nearest_survey_distance_km`
- `survey_density`
- `extrapolation_flag`
- `reliability_status`

Uncertainty must come from the actual fitted model or validation procedure.

---

## 4.3 Population at Risk API

**Owner:** Backend Engineer, with ML Engineer supplying outputs.

### GET `/population-at-risk/`

Query parameters:

- `country`
- `year`
- `region_id`

Risk classes:

| Class | PfPR |
|---|---|
| Very low | Below 1% |
| Low | 1% to below 10% |
| Moderate | 10% to below 35% |
| High | 35% and above |

Response fields:

- `country`
- `region_id`
- `year`
- `risk_class`
- `population`
- `population_source`
- `prevalence_model_version`
- `uncertainty_status`

Population estimates must not be described as infected population counts.

---

## 4.4 Species API

**Owners:** ML Engineer and Backend Engineer

### GET `/species/`

Query parameters:

- `country`
- `region_id`
- `species`
- `year`

Supported species:

- Plasmodium falciparum
- Plasmodium vivax
- Plasmodium malariae
- Plasmodium ovale
- Plasmodium knowlesi

Response:

```json
{
  "success": true,
  "data": [
    {
      "country": "ETH",
      "region_id": "REGION_ID",
      "species": "P. vivax",
      "record_type": "survey",
      "positive": null,
      "examined": null,
      "year": null,
      "source_id": null,
      "evidence_ids": []
    }
  ]
}
```

### Rules

- Presence-only records must be labelled as presence-only.
- Missing species evidence must be reported as unavailable.
- District-level species shares require denominator-bearing data.
- Never derive case shares from GBIF occurrence records alone.

---

## 4.5 Drug Efficacy API

**Owners:** ML Engineer and Backend Engineer

### GET `/drugs/efficacy/`

Query parameters:

- `country`
- `region_id`
- `drug`
- `followup_days`

Example:

`GET /drugs/efficacy/?country=KEN&drug=AL&followup_days=28`

Response fields:

- `study_id`
- `country`
- `region_id`
- `drug`
- `followup_days`
- `n_patients`
- `acpr_percent`
- `failure_percent`
- `confidence_interval_lower`
- `confidence_interval_upper`
- `prediction_interval_lower`
- `prediction_interval_upper`
- `heterogeneity_i2`
- `study_count`
- `year_range`
- `source_id`
- `evidence_ids`

### Rules

- Preserve PCR-corrected efficacy definitions.
- Do not mix day 28 and day 42 follow-up estimates.
- Report study counts and patient counts.
- Do not interpret trial efficacy as guaranteed real-world effectiveness.
- The 10% treatment failure threshold is an evidence interpretation reference, not an automated treatment recommendation.

---

## 4.6 Resistance API

**Owners:** ML Engineer and Backend Engineer

### GET `/resistance/`

Query parameters:

- `country`
- `region_id`
- `marker`
- `year`

Response fields:

- `country`
- `region_id`
- `marker`
- `year`
- `n_tested`
- `n_mutant`
- `frequency`
- `confidence_interval_lower`
- `confidence_interval_upper`
- `source_id`
- `evidence_ids`

Supported markers should be restricted to the validated mutations or marker definitions used in the project.

### GET `/resistance/trends/`

Returns marker trends and modelled estimates.

Include:

- Observed frequency.
- Predicted frequency.
- Sample denominator.
- Confidence interval.
- Validation method.
- Source and year.

A resistance marker frequency is not equivalent to clinical treatment failure.

---

## 4.7 Environmental Conditions API

**Owner:** Backend Engineer

### GET `/environment/current/`

Query parameters:

- `country`
- `region_id`
- `latitude`
- `longitude`

Returns available current weather conditions.

Response fields:

- `temperature_c`
- `relative_humidity_percent`
- `precipitation_mm`
- `wind_speed_kmh`
- `observed_at`
- `provider`
- `retrieved_at`

### GET `/environment/history/`

Query parameters:

- `country`
- `region_id`
- `start_date`
- `end_date`

Returns historical weather observations or reanalysis data, depending on the provider.

Response fields:

- `date`
- `temperature_mean_c`
- `temperature_min_c`
- `temperature_max_c`
- `precipitation_mm`
- `relative_humidity_percent`
- `provider`
- `data_type`

### Rules

- Label forecasts, historical weather, current conditions and climatological averages separately.
- Include provider and retrieval timestamps.
- Cache API results.
- Do not treat current weather as current malaria prevalence.
- Weather data is an additional monitoring feature, not a substitute for the historical covariates used in the prevalence model.

---

# 5. AI Assistant API

**Owners:** Shared responsibility

Engineer 1 provides the data retrieval services.

Engineer 2 provides validated model outputs.

The architect integrates the React interface and agent workflow.

## 5.1 Generate a briefing

### POST `/assistant/brief/`

Request:

```json
{
  "country": "KEN",
  "region_id": "REGION_ID",
  "question": "Summarise the available malaria surveillance evidence for this region."
}
```

Response:

```json
{
  "success": true,
  "data": {
    "brief_id": "BRIEF_ID",
    "status": "draft",
    "country": "KEN",
    "region_id": "REGION_ID",
    "summary": "Pending evidence retrieval.",
    "findings": [],
    "evidence_ids": [],
    "uncertainties": [],
    "limitations": [],
    "tool_trace_id": "TRACE_ID",
    "created_at": "2026-11-12T09:00:00Z"
  }
}
```

## 5.2 Review a briefing

### POST `/assistant/review/`

Request:

```json
{
  "brief_id": "BRIEF_ID",
  "decision": "approve",
  "reviewer": "REVIEWER_ID",
  "edited_content": null
}
```

Allowed decisions:

- approve
- edit
- reject

Only approved briefs may be exported as approved briefings.

The application must preserve the original draft, reviewer decision and review timestamp.

## 5.3 Agent logs

### GET `/assistant/logs/`

Returns:

- Run identifier.
- Question.
- Guardrail decision.
- Tool name.
- Tool arguments.
- Tool result.
- Evidence identifiers.
- Draft output.
- Grounding result.
- Reviewer decision.
- Timestamp.

Do not log secrets, personal data or sensitive information.

---

# 6. Shared Evidence Object

All scientific modules must use consistent evidence references.

Recommended object:

```json
{
  "evidence_id": "E001",
  "source_name": "Example public dataset",
  "source_url": null,
  "publication_year": null,
  "accessed_at": "2026-11-12",
  "license": "VERIFY_LICENSE",
  "evidence_type": "survey",
  "country": "KEN",
  "limitations": []
}
```

This is a schema example, not a claim that a particular source has been accessed or licensed.

Every scientific number returned by an API must be traceable to an evidence reference or an identified model output.

# 7. ML-to-Backend Integration Contract

The ML engineer must export machine-readable outputs.

Required output datasets:

| Output | Format |
|---|---|
| Prevalence grid | GeoParquet |
| District prevalence | Parquet |
| Uncertainty results | Parquet |
| Population at risk | Parquet |
| Species records | Parquet |
| Efficacy estimates | Parquet |
| Resistance trends | Parquet |
| Model metrics | JSON |
| Model metadata | JSON |

Each model output must include:

- Model name and version.
- Prediction year.
- Country and geographic identifier.
- Source data references.
- Evaluation method.
- Uncertainty information.
- Generation timestamp.

The backend engineer must not invent missing ML values or silently replace unavailable results with fabricated values.

# 8. Frontend Integration Rules

The React application consumes API data through a centralized service layer.

Suggested structure:

```text
frontend/src/
├── services/
│   ├── api.js
│   ├── geography.js
│   ├── prevalence.js
│   ├── species.js
│   ├── drugs.js
│   ├── resistance.js
│   ├── environment.js
│   └── assistant.js
│
├── components/
├── pages/
├── layouts/
├── hooks/
└── charts/
```

Rules:

1. Never hardcode scientific statistics.
2. Show loading, empty and error states.
3. Display source and year.
4. Distinguish observed and modelled data.
5. Display uncertainty when available.
6. Show a clear no-data message.
7. Never hide missing evidence.

# 9. API Security and Reliability

- Use environment variables for secrets.
- Configure CORS for approved frontend origins.
- Validate query parameters and geographic identifiers.
- Apply reasonable rate limits.
- Do not expose internal database credentials.
- Do not accept patient-level health information.
- Do not send private information to hosted AI services.
- Cache external weather requests.
- Use structured logging.
- Restrict approval operations to authorised reviewers.

Authentication can remain lightweight for the local hackathon demo, but approval operations must not be exposed as unrestricted public actions.

# 10. Testing Requirements

Backend tests:

- Valid country filtering.
- Invalid country rejection.
- Geographic identifier validation.
- Missing data handling.
- Prevalence response schema.
- Uncertainty response schema.
- Weather provider error handling.
- Evidence ID consistency.
- Brief approval and rejection.
- Agent logging.

Frontend tests:

- API loading states.
- Empty data states.
- Error handling.
- Country filters.
- Map rendering.
- Chart rendering.
- Source labels.
- Brief approval workflow.

Integration tests:

- ML output to backend.
- Backend to frontend.
- Evidence retrieval to AI brief.
- Brief generation to human approval.

# 11. Engineer Ownership

| Component | Owner |
|---|---|
| React frontend | Architect / Frontend |
| UI/UX | Architect |
| API specification | Architect |
| Django backend | Backend Engineer |
| Database and PostGIS | Backend Engineer |
| Data ingestion | Backend Engineer |
| Weather integration | Backend Engineer |
| Prevalence modelling | ML Engineer |
| Spatial validation | ML Engineer |
| Species analysis | ML Engineer |
| Drug efficacy analysis | ML Engineer |
| Resistance modelling | ML Engineer |
| Agent tools | Backend + ML |
| Agent interface and integration | Architect |
| Final integration and review | Architect |

# 12. Integration Milestones

**CP1: Contract approval**

All engineers agree on endpoint names, field definitions and output schemas.

**CP2: Backend foundation**

Django responds with valid API structures and database connectivity.

**CP3: ML foundation**

Prevalence model, baseline and spatial validation produce reproducible outputs.

**CP4: API integration**

Django exposes actual ML results.

**CP5: Frontend integration**

React renders real geographic data and scientific results.

**CP6: AI integration**

The assistant retrieves evidence, cites sources, logs calls and supports human approval.

**CP7: Final verification**

Tests pass, documentation is complete and the application can be reproduced.

---

# 13. Non-negotiable Scientific Rules

1. Never fabricate statistics or study results.
2. Never present modelled predictions as observed measurements.
3. Never derive species case shares from presence-only records.
4. Never interpret resistance markers as direct treatment failure.
5. Never provide individual diagnosis or dosing.
6. Always report uncertainty and data limitations.
7. Every scientific claim must have traceable evidence.
8. Human approval is required before a briefing is marked approved.
9. Clearly label synthetic, observed, modelled and forecast data.
10. If evidence is unavailable, return an explicit no-data status.

---

**END OF API CONTRACT**

Malaria WatchAI | Technical Architecture Specification | Version 1.0
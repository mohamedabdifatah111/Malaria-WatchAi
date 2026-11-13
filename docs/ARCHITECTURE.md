# MalariaWatchAI Backend Architecture

## 1. Overview

MalariaWatchAI is a geospatial malaria surveillance and evidence analysis platform designed to support the exploration of malaria prevalence, environmental conditions, population exposure, parasite species, antimalarial drug efficacy and resistance evidence.

The backend provides a centralized API for the frontend and other system components. It manages geographic data, scientific evidence, environmental information, and AI-assisted access to malaria-related knowledge.

The system is designed to support malaria surveillance across selected study areas in Kenya, Tanzania and Ethiopia.

## 2. Architecture Goals

The backend architecture aims to:

- Provide a centralized and documented REST API.
- Store geographic and scientific data reliably.
- Support spatial queries and geographic analysis.
- Integrate environmental information from external providers.
- Maintain traceability of scientific evidence and data sources.
- Distinguish observed, modelled and synthetic information.
- Provide a foundation for AI-assisted evidence exploration.
- Support future expansion to additional regions and datasets.

## 3. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend language | Python 3.13 | Application logic and data processing |
| Web framework | Django 5.2 | Backend application framework |
| API framework | Django REST Framework | REST API development |
| Database | PostgreSQL 18 | Relational data storage |
| Spatial database | PostGIS | Geographic data storage and spatial queries |
| API documentation | Swagger / OpenAPI | API discovery and documentation |
| Testing | Pytest and pytest-django | Automated backend testing |
| Environmental data | Open-Meteo | Weather and historical climate information |
| AI integration | Google Gemini API | AI-assisted information processing |
| Frontend integration | React, TypeScript and MapLibre GL JS | User interface and geographic visualization |

## 4. High-Level Architecture

The application follows a layered architecture.

```text
                  USER
                    |
                    v
          REACT FRONTEND
          TypeScript / MapLibre
                    |
                    v
              REST API
       Django REST Framework
                    |
          +---------+---------+
          |         |         |
          v         v         v
       Geography  Evidence  Environment
          |         |         |
          +---------+---------+
                    |
                    v
           APPLICATION SERVICES
       Scientific and spatial logic
                    |
          +---------+---------+
          |                   |
          v                   v
      PostgreSQL           External APIs
       + PostGIS            Open-Meteo
          |
          v
       GEOGRAPHIC AND SCIENTIFIC DATA

                    |
                    v
             AI ASSISTANT
              Gemini API
       Evidence-grounded responses
```

The diagram represents the intended system architecture. Individual integrations and capabilities should be considered implemented only where the corresponding code and configuration are present.

## 5. Backend Application Structure

The backend is organized into Django applications, with each application responsible for a specific functional area.

### 5.1 Core

Responsible for shared backend functionality, including:

- Common API response structures.
- Health checks.
- Shared utilities.
- System-level configuration.

### 5.2 Geography

Responsible for geographic information, including:

- Country records.
- Administrative regions.
- Geographic identifiers.
- Region relationships.
- Spatial filtering and geographic queries.

PostGIS supports spatial operations and geographic data management.

### 5.3 Evidence

Responsible for scientific evidence management.

It provides a foundation for:

- Recording evidence sources.
- Tracking source identifiers.
- Maintaining data provenance.
- Recording licence and access information.
- Distinguishing validated evidence from synthetic records.

Evidence traceability is important because malaria-related outputs must be linked to their underlying sources.

### 5.4 Environment

Responsible for environmental information.

The application integrates with Open-Meteo to retrieve environmental data such as:

- Temperature.
- Relative humidity.
- Precipitation.
- Wind speed.
- Historical weather information.

Environmental observations and model-based estimates must be identified correctly. Weather information must not be interpreted as direct evidence of malaria prevalence.

### 5.5 Science

Responsible for malaria-related scientific information and analysis.

The planned scientific domains include:

- Malaria prevalence.
- Parasite species.
- Antimalarial drug efficacy.
- Antimalarial resistance.
- Population at risk.
- Statistical summaries and uncertainty.

Scientific outputs should preserve their source, reference period, methodology and uncertainty.

### 5.6 Assistant

Responsible for AI-assisted information access.

The intended integration uses Google's Gemini API.

The assistant is designed to help users explore available malaria evidence and interpret system outputs.

AI responses should:

- Use available evidence rather than inventing facts.
- Identify supporting evidence sources.
- Communicate uncertainty.
- Indicate when information is unavailable.
- Avoid diagnosing patients or prescribing treatment.
- Require human review where appropriate.

The assistant must not replace qualified medical or public health professionals.

## 6. Database Architecture

PostgreSQL is the primary relational database.

PostGIS extends PostgreSQL with spatial data types and geographic operations.

The database is intended to store:

- Countries.
- Administrative regions.
- Geographic boundaries.
- Prevalence estimates.
- Environmental records.
- Population information.
- Parasite species records.
- Drug efficacy studies.
- Resistance evidence.
- Evidence sources.
- Assistant activity records.

Geographic records should use reliable administrative identifiers and validated boundaries. Region names alone should not be used as the only matching mechanism.

## 7. API Architecture

The backend exposes versioned REST endpoints under:

`/api/v1/`

The API is organized by functional domain.

| Domain | Endpoint | Method |
|---|---|---|
| System | `/api/v1/health/` | GET |
| Geography | `/api/v1/countries/` | GET |
| Geography | `/api/v1/regions/` | GET |
| Geography | `/api/v1/regions/{id}/` | GET |
| Prevalence | `/api/v1/prevalence/` | GET |
| Prevalence | `/api/v1/prevalence/map/` | GET |
| Prevalence | `/api/v1/prevalence/uncertainty/` | GET |
| Environment | `/api/v1/environment/current/` | GET |
| Environment | `/api/v1/environment/history/` | GET |
| Population | `/api/v1/population-at-risk/` | GET |
| Species | `/api/v1/species/` | GET |
| Drugs | `/api/v1/drugs/efficacy/` | GET |
| Resistance | `/api/v1/resistance/` | GET |
| Resistance | `/api/v1/resistance/trends/` | GET |
| Assistant | `/api/v1/assistant/brief/` | POST |
| Assistant | `/api/v1/assistant/review/` | POST |
| Assistant | `/api/v1/assistant/logs/` | GET |
| Authentication | `/api/v1/auth/token/` | POST |

Interactive API documentation is available at:

`/api/v1/docs/`

## 8. API Response Design

API responses use a consistent structure.

Successful response example:

```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2026-11-13T00:00:00Z",
    "source": "malaria-watchai"
  }
}
```

Responses may also include pagination metadata, data status and explanatory messages.

When validated data is unavailable, the API should return an explicit no-data response.

An empty dataset must never be interpreted as zero malaria prevalence, zero resistance or absence of disease.

## 9. Environmental Data Flow

The environmental integration follows this general process:

1. The frontend requests current or historical environmental information.
2. Django receives and validates the request.
3. The environment service communicates with Open-Meteo.
4. The returned information is normalized into the backend response structure.
5. Provider and retrieval information are included.
6. The frontend receives the response for display.

Environmental information provides supporting context for malaria surveillance. It does not independently establish malaria transmission or prevalence.

## 10. Geospatial Data Flow

The intended geographic workflow is:

1. Geographic boundaries and administrative identifiers are prepared.
2. Geographic records are validated.
3. Validated data is stored in PostgreSQL/PostGIS.
4. The API retrieves geographic and malaria-related records.
5. Spatial queries support geographic filtering and map responses.
6. GeoJSON responses can be consumed by the frontend.
7. MapLibre GL JS displays geographic information.

Geographic boundaries must retain their administrative level and source identifiers.

## 11. Scientific Data and Model Integration

The platform is designed to support geospatial malaria analysis using epidemiological and environmental datasets.

Potential model inputs include:

- Historical malaria prevalence surveys.
- Temperature.
- Rainfall.
- Vegetation indices.
- Elevation.
- Distance to water.
- Population density.
- Urban and rural classifications.

Scientific model outputs should include:

- Reference period.
- Geographic resolution.
- Model methodology.
- Data sources.
- Validation metrics.
- Prediction uncertainty.
- Limitations.

Modelled estimates must be clearly distinguished from observed survey results.

A model should not be described as trained or validated until the required data has been loaded and the training and evaluation processes have actually been completed.

## 12. Security and Reliability

The backend should follow these security principles:

- Store API credentials in environment variables.
- Never commit private `.env` files.
- Validate incoming API parameters.
- Apply appropriate authentication and permissions.
- Restrict access to administrative operations.
- Use HTTPS in production.
- Avoid exposing sensitive information in API responses.
- Log relevant system and assistant activities.
- Avoid collecting unnecessary personal or patient-identifiable information.

## 13. Testing Strategy

The backend uses Pytest and pytest-django for automated testing.

The current test suite contains 116 tests, all of which passed in the recorded test run.

Test coverage includes:

- Assistant functionality.
- Core functionality.
- Environmental services.
- Evidence management.
- Geospatial operations.
- Geographic functionality.
- Scientific logic.
- Statistical operations.

Test command:

```bash
python -m pytest -v
```

The passing test suite confirms that the tested functionality behaves as expected under the test conditions. It does not independently establish production readiness or the accuracy of external scientific datasets.

## 14. Current Limitations and Future Improvements

The following areas require continued development and validation:

- Importing and validating administrative geographic boundaries.
- Populating the database with validated malaria prevalence data.
- Integrating population datasets.
- Expanding validated parasite species records.
- Adding validated drug efficacy and resistance evidence.
- Training and evaluating spatial prediction models.
- Completing AI assistant integration and evidence-grounding validation.
- Verifying external data licences and attribution requirements.
- Conducting production security and deployment checks.

The system should communicate data availability honestly and avoid presenting unavailable datasets as established scientific results.

## 15. Conclusion

MalariaWatchAI uses a modular Django backend supported by PostgreSQL and PostGIS to provide geographic, environmental and scientific information through a versioned REST API.

Its architecture provides a foundation for combining malaria evidence, spatial analysis, environmental information and AI-assisted exploration in one platform.

The design prioritizes data provenance, scientific transparency, geographic accuracy and responsible interpretation of malaria-related information.

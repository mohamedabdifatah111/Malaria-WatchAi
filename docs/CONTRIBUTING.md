# Contributing to MalariaWatchAI

Thank you for your interest in contributing to MalariaWatchAI.

MalariaWatchAI is a geospatial malaria surveillance and evidence analysis platform designed to support malaria monitoring, scientific research and public health decision-making across selected regions in Kenya, Tanzania and Ethiopia.

This document explains the contribution guidelines for developers, researchers and other project collaborators.

## 1. Project Goals

Contributions should support one or more of the following objectives:

- Improving malaria surveillance and geographic analysis.
- Integrating reliable malaria and environmental datasets.
- Improving scientific accuracy and data quality.
- Developing and maintaining backend APIs.
- Improving frontend functionality and map visualization.
- Developing and validating machine learning models.
- Improving AI-assisted evidence exploration.
- Strengthening documentation, testing and security.

## 2. Project Structure

The project contains separate frontend and backend components.

```text
malaria-watchai/
│
├── backend/
│   ├── apps/
│   ├── config/
│   ├── tests/
│   ├── manage.py
│   └── pytest.ini
│
├── frontend/
│   └── ...
│
├── docs/
│   └── ...
│
├── README.md
├── ARCHITECTURE.md
└── CONTRIBUTING.md
```

The actual directory structure may evolve as development progresses.

## 3. Development Requirements

Contributors working on the backend should have:

- Python 3.13 or compatible version.
- Django 5.2.
- Django REST Framework.
- PostgreSQL.
- PostGIS.
- Git.
- A code editor such as Visual Studio Code.

Frontend contributors should have:

- Node.js.
- npm.
- React.
- TypeScript.
- Vite.
- MapLibre GL JS.

Additional dependencies should be installed according to the relevant component's requirements.

## 4. Getting Started

### Step 1: Obtain the project

Clone the project repository if you have access to its shared remote repository.

```bash
git clone <repository-url>
cd malaria-watchai
```

### Step 2: Set up the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows:

```cmd
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Configure the required environment variables using the project's `.env.example` as a reference.

### Step 3: Configure the database

Create and configure a PostgreSQL database with the required PostGIS extension.

Update the local environment configuration with the appropriate database connection details.

### Step 4: Apply database migrations

```bash
python manage.py migrate
```

### Step 5: Run the backend

```bash
python manage.py runserver
```

### Step 6: Run automated tests

```bash
python -m pytest -v
```

Contributors should ensure that relevant tests pass before submitting changes.

## 5. Contribution Workflow

Contributions should follow this workflow:

1. Identify an issue or improvement.
2. Understand the relevant application component.
3. Make changes in a separate branch when working with a shared repository.
4. Write or update relevant tests.
5. Run the test suite.
6. Review the changes for correctness and security.
7. Submit the changes for review.

Suggested branch naming:

```text
feature/short-description
fix/short-description
docs/short-description
test/short-description
```

## 6. Coding Guidelines

### Backend

- Follow Python conventions and PEP 8.
- Use meaningful function, class and variable names.
- Keep Django applications modular.
- Use serializers to validate API input and output.
- Avoid unnecessary duplication.
- Handle errors consistently.
- Document complex scientific and geospatial operations.

### Frontend

- Use TypeScript where applicable.
- Keep components reusable.
- Maintain consistent API integration.
- Handle loading, error and no-data states.
- Clearly distinguish missing data from zero values.

### Database

- Use appropriate field types and relationships.
- Preserve geographic identifiers.
- Avoid destructive migrations without review.
- Maintain data integrity and provenance.

## 7. Scientific and Data Contribution Guidelines

Scientific accuracy is a core requirement.

Contributors adding datasets or scientific results should:

- Identify the original data source.
- Record the publication or collection date.
- Record geographic coverage.
- Document the methodology.
- Include licence and attribution information.
- Distinguish observed data from modelled estimates.
- Identify synthetic or demonstration data clearly.
- Document limitations and uncertainty.

Do not present synthetic data as real epidemiological evidence.

Do not interpret missing records as zero malaria prevalence or absence of disease.

Model outputs must not be described as validated unless appropriate evaluation has been performed.

## 8. AI Contribution Guidelines

AI-related contributions should prioritize accuracy, transparency and responsible use.

The assistant should:

- Ground factual claims in available evidence.
- Identify supporting evidence where possible.
- Communicate uncertainty.
- Avoid fabricating scientific references.
- Clearly indicate when information is unavailable.
- Avoid providing patient diagnoses or treatment prescriptions.
- Support human review of important public health conclusions.

Google Gemini API credentials must be stored securely and must never be committed to the repository.

## 9. Testing Requirements

Changes should include appropriate tests.

Backend contributors should run:

```bash
python -m pytest -v
```

Tests should cover relevant functionality, including:

- API behavior.
- Input validation.
- Database operations.
- Geographic queries.
- Scientific calculations.
- Evidence traceability.
- Error handling.
- AI safety behavior where applicable.

Do not submit changes that knowingly break existing tests.

## 10. Commit Message Guidelines

Use clear and descriptive commit messages.

Examples:

```text
feat: add regional prevalence filtering
fix: correct geographic query validation
test: add evidence service tests
docs: update backend architecture
refactor: improve environment service structure
```

## 11. Security and Privacy

Contributors must:

- Never commit passwords, API keys or private credentials.
- Never upload patient-identifiable information.
- Avoid exposing sensitive system information.
- Validate external input.
- Use secure configuration practices.
- Report potential security vulnerabilities privately to the project maintainers rather than publishing exploit details.

## 12. Documentation

Contributors should update relevant documentation whenever functionality changes.

Documentation may include:

- README.md
- ARCHITECTURE.md
- CONTRIBUTING.md
- API documentation
- Data documentation
- Scientific assumptions
- Model cards
- Setup instructions

Documentation should describe the actual implementation and avoid claiming incomplete functionality as finished.

## 13. Code Review

Contributions should be reviewed for:

- Correctness.
- Maintainability.
- Security.
- Scientific reliability.
- Test coverage.
- Documentation quality.
- Compatibility with the existing architecture.

Changes involving scientific methods, epidemiological interpretation or public health recommendations require particular care.

## 14. Acknowledgements

Contributors should receive appropriate recognition for their work.

Contributions may include software development, scientific research, data preparation, testing, documentation, design and project coordination.

External datasets, libraries, APIs and AI tools should be acknowledged according to their respective licence and attribution requirements.

## 15. Code of Conduct

All contributors are expected to:

- Treat other contributors respectfully.
- Communicate constructively.
- Welcome feedback.
- Respect different perspectives.
- Prioritize scientific integrity.
- Avoid misleading claims about project capabilities or results.

## 16. Final Note

MalariaWatchAI is intended to support evidence-based malaria surveillance and research.

Every contribution should help make the platform more reliable, transparent, accessible and scientifically responsible.

Thank you for contributing to MalariaWatchAI.
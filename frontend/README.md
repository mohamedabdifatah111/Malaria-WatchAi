# MalariaWatchAI - frontend

React 19 + TypeScript + Vite + Tailwind CSS 4, with React Router, TanStack Query, Axios,
Recharts, React Leaflet and Lucide icons. Talks only to the Django REST API (`/api/v1/`).

## Run

```bash
cd frontend
npm install
cp .env.example .env.local      # set VITE_API_BASE_URL (default http://localhost:8000)
npm run dev                     # http://localhost:5173
```

The backend must allow the dev origin (`CORS_ALLOWED_ORIGINS=http://localhost:5173` in the
root `.env`). Sign in with a backend account (`POST /api/v1/auth/token/`).

```bash
npm test          # vitest: utilities, API handling, components, pages (mocked API)
npm run typecheck
npm run build     # type-check + production build to dist/
```

The frontend holds no secrets. The Gemini key is used by the backend only; never put a key in a
`VITE_*` variable (those are bundled into public JavaScript).

## Pages

| Route | Endpoints |
|---|---|
| `/login` | `POST auth/token/` |
| `/dashboard` | prevalence, prevalence/uncertainty, population-at-risk, species, drugs/efficacy, resistance |
| `/map` | `prevalence/map/` (GeoJSON), `regions/?include_boundary=true` for areas with no estimate |
| `/prevalence` | `prevalence/`, `prevalence/uncertainty/` |
| `/species` | `species/` |
| `/environment` | `environment/current/`, `environment/history/` |
| `/population-risk` | `population-at-risk/` |
| `/drug-efficacy` | `drugs/efficacy/` |
| `/resistance` | `resistance/`, `resistance/trends/` |
| `/assistant`, `/briefs` | `POST assistant/brief/` |

## Data display rules (enforced in `src/utils/format.ts`, tested)

- Prevalence `estimate`/intervals and marker `frequency` are fractions 0-1 and are multiplied by
  100 for display. Efficacy fields are already percentages and are never multiplied.
- `null` is always "Not available" - never 0. Areas without an estimate are grey "No estimate" on
  the map, never coloured as zero.
- Observed vs modelled is written in words (badges), not colour alone; risk classes are labelled.
- Presence-only species records are labelled "Presence observation only" and never produce a rate
  or share.
- Every table shows evidence ids; empty responses show the backend's own no-data message.

## Backend contract mismatches and gaps (for the backend engineer)

1. **Brief findings shape** - the frontend specification described `findings: [{ text }]`; the
   backend sends `{ topic, statement, evidence_ids }`. The UI renders `statement` and accepts
   `text`, so both work; please confirm the intended contract.
2. **No brief list endpoint** - only `POST assistant/brief/` and the reviewer-only
   `GET assistant/logs/` exist, so "Brief history" covers briefs generated in this browser session.
   Requested: `GET /api/v1/assistant/briefs/` (non-reviewer, own briefs).
3. **Synthetic flag not exposed** - `EvidenceSource.evidence_type` can be `synthetic`, but list
   serializers return only `evidence_ids`/`source_id`, so the UI cannot label synthetic records.
   Requested: an `evidence_type` or `data_classification` field on science serializers.
4. **No current-user / role endpoint** - the UI cannot know if a user is a reviewer; approval is
   therefore not shown (as required until the auth model is agreed).
5. **Survey-location count** - endpoint does not exist; the dashboard shows an "unavailable" KPI.
6. **Country-level values** - prevalence and population-at-risk rows are regional (ADM1/ADM2);
   the UI does not sum regions into national totals.
7. **Weather location** - `environment/*` needs `region_id` (region with a boundary) or
   `latitude`+`longitude`; a country alone is rejected, so the page asks for one of these.
8. **Tokens do not expire** (DRF TokenAuthentication); the UI treats any 401 as an ended session.

## Status

- Type-check, production build and 28 automated tests pass.
- **Not yet tested against a running backend**: it was built from the backend serializers and
  tested with mocked responses in those exact shapes. Run it against the backend (with ML outputs
  imported) before the demo and record results in the pull request.

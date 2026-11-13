/**
 * API types, written from the Django REST serializers on the backend
 * (backend/apps/<app>/serializers.py) - the backend is the source of truth.
 * Nullable fields are typed as `| null`: a null is "not available", never zero.
 */

import type { Feature, Geometry } from "geojson";

export type CountryCode = "KEN" | "TZA" | "ETH";
export type AdminLevel = "ADM1" | "ADM2";
export type SourceType = "observed" | "modelled";

/** Every response is wrapped by apps.core.renderers.EnvelopeJSONRenderer. */
export interface Envelope<T> {
  success: true;
  data: T;
  meta: {
    timestamp?: string;
    source?: string;
    data_status?: "available" | "no_data";
    message?: string;
    pagination?: Pagination;
  };
}

export interface Pagination {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
}

export interface Paged<T> {
  items: T[];
  pagination: Pagination | null;
  dataStatus: "available" | "no_data";
  message?: string;
}

export interface ApiErrorBody {
  success: false;
  error: { code: string; message: string; details?: unknown };
}

/** apps.geography: CountrySerializer */
export interface Country {
  code: CountryCode;
  name: string;
}

/** apps.geography: RegionSerializer (boundary only when include_boundary=true) */
export interface Region {
  id: number;
  name: string;
  country_code: CountryCode;
  admin_level: AdminLevel;
  parent_id: number | null;
  external_id: string;
  boundary?: Geometry | null;
}

/** apps.prevalence: PrevalenceEstimateSerializer. `estimate` is a FRACTION 0-1. */
export interface PrevalenceEstimate {
  country: CountryCode;
  region_id: number;
  region_name: string;
  year: number;
  indicator: string;
  estimate: number;
  lower_interval: number | null;
  upper_interval: number | null;
  source_type: SourceType;
  model_version: string;
  evidence_ids: string[];
  status: string;
}

/** apps.prevalence: PrevalenceUncertaintySerializer */
export interface PrevalenceUncertainty {
  region_id: number;
  year: number;
  estimate: number;
  lower_interval: number | null;
  upper_interval: number | null;
  interval_width: number | null;
  nearest_survey_distance_km: number | null;
  survey_density: number | null;
  extrapolation_flag: boolean | null;
  reliability_status: string;
  evidence_ids: string[];
}

/** apps.prevalence: PrevalenceMapView feature properties */
export interface PrevalenceMapProperties {
  feature_id: string;
  region_id: number;
  region_name: string;
  country: CountryCode;
  year: number;
  indicator: string;
  estimate: number;
  lower_interval: number | null;
  upper_interval: number | null;
  source_type: SourceType;
  model_version: string | null;
  evidence_ids: string[];
}

export interface PrevalenceMap {
  type: "FeatureCollection";
  features: Feature<Geometry, PrevalenceMapProperties>[];
  feature_count: number;
  total_matching: number;
  truncated: boolean;
  data_status: "available" | "no_data";
}

export type RiskClass = "very_low" | "low" | "moderate" | "high";

/** apps.population: PopulationAtRiskSerializer. People living in a class - NOT infections. */
export interface PopulationAtRisk {
  country: CountryCode;
  region_id: number;
  year: number;
  risk_class: RiskClass;
  population: number;
  population_source: string;
  prevalence_model_version: string;
  uncertainty_status: string;
  evidence_ids: string[];
}

export type SpeciesName = "P. falciparum" | "P. vivax" | "P. malariae" | "P. ovale" | "P. knowlesi";
export type SpeciesRecordType = "survey" | "presence_only" | "modelled";

/** apps.species: SpeciesRecordSerializer. presence_only rows carry no counts. */
export interface SpeciesRecord {
  country: CountryCode;
  region_id: number | null;
  species: SpeciesName;
  record_type: SpeciesRecordType;
  positive: number | null;
  examined: number | null;
  year: number;
  source_id: string;
  evidence_ids: string[];
}

/** apps.drug_efficacy: DrugEfficacySerializer. Percent fields are 0-100. */
export interface DrugEfficacy {
  record_type: "study" | "pooled";
  study_id: string | null;
  country: CountryCode;
  region_id: number | null;
  site: string;
  drug: string;
  followup_days: number;
  n_patients: number;
  acpr_percent: number;
  failure_percent: number | null;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  prediction_interval_lower: number | null;
  prediction_interval_upper: number | null;
  heterogeneity_i2: number | null;
  study_count: number | null;
  year_range: string;
  source_id: string;
  evidence_ids: string[];
}

/** apps.resistance: ResistanceObservationSerializer. frequency is a FRACTION 0-1. */
export interface ResistanceObservation {
  country: CountryCode;
  region_id: number | null;
  marker: string;
  year: number;
  n_tested: number;
  n_mutant: number;
  frequency: number;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  source_id: string;
  evidence_ids: string[];
}

/** apps.resistance: MarkerTrendSerializer. Frequencies are FRACTIONS 0-1. */
export interface MarkerTrend {
  country: CountryCode;
  region_id: number | null;
  marker: string;
  year: number;
  observed_frequency: number | null;
  predicted_frequency: number | null;
  n_tested: number | null;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  validation_method: string;
  model_version: string;
  source_id: string;
  evidence_ids: string[];
}

/** apps.environment: CurrentWeatherView */
export interface CurrentWeather {
  status: string;
  country: CountryCode | null;
  region_id: number | null;
  latitude: number;
  longitude: number;
  data_type: "current";
  temperature_c: number | null;
  relative_humidity_percent: number | null;
  precipitation_mm: number | null;
  wind_speed_kmh: number | null;
  observed_at: string;
  provider: string;
  retrieved_at: string;
  evidence_ids: string[];
  notes: string[];
}

export interface WeatherDay {
  date: string;
  temperature_mean_c: number | null;
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  precipitation_mm: number | null;
  relative_humidity_percent: number | null;
  provider: string;
}

/** apps.environment: WeatherHistoryView */
export interface WeatherHistory {
  status: string;
  country: CountryCode | null;
  region_id: number | null;
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
  data_type: string;
  provider: string;
  retrieved_at: string;
  evidence_ids: string[];
  notes: string[];
  records: WeatherDay[];
}

/**
 * apps.assistant: brief findings as built by services/brief_builder.py.
 * CONTRACT NOTE: the frontend brief specified `{ text }`; the backend sends
 * `{ topic, statement, evidence_ids }`. We render `statement` and accept `text`.
 */
export interface BriefFinding {
  topic?: string;
  statement?: string;
  text?: string;
  evidence_ids?: string[];
}

export type BriefStatus = "draft" | "edited" | "approved" | "rejected";

/** apps.assistant: BriefSerializer */
export interface Brief {
  brief_id: string;
  status: BriefStatus;
  country: CountryCode;
  region_id: number | null;
  summary: string;
  findings: BriefFinding[];
  evidence_ids: string[];
  uncertainties: string[];
  limitations: string[];
  tool_trace_id: string;
  created_at: string;
  edited_content: unknown | null;
  review: { decision: string; reviewer: string | null; reviewed_at: string } | null;
}

export interface BriefRequest {
  country: CountryCode;
  region_id: number | null;
  question: string;
}

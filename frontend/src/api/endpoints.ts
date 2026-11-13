/**
 * One function per backend endpoint (backend/config/urls.py). Filters are the
 * django-filter fields each endpoint declares in backend/apps/<app>/filters.py.
 */
import { api, getOne, getPaged, unwrap } from "./client";
import type {
  Brief,
  BriefRequest,
  Country,
  CountryCode,
  CurrentWeather,
  DrugEfficacy,
  Envelope,
  MarkerTrend,
  PopulationAtRisk,
  PrevalenceEstimate,
  PrevalenceMap,
  PrevalenceUncertainty,
  Region,
  ResistanceObservation,
  SpeciesRecord,
  WeatherHistory,
} from "../types/api";

export interface GeoFilter {
  country?: CountryCode | "";
  region_id?: number | null;
  year?: number | null;
}

// ---- auth ---------------------------------------------------------------
export async function login(username: string, password: string): Promise<string> {
  const r = await api.post<Envelope<{ token: string }>>("auth/token/", { username, password });
  return unwrap(r.data).token;
}

// ---- geography ----------------------------------------------------------
export async function getCountries(): Promise<Country[]> {
  // Countries are not paginated in the backend; accept either shape.
  const r = await api.get<Envelope<Country[]>>("countries/");
  const data = unwrap(r.data);
  return Array.isArray(data) ? data : [];
}

/** All regions for a country/level, following pagination (page_size max is 200; Kenya has 290 ADM2). */
export async function getRegions(f: { country?: string; level?: string; search?: string }): Promise<Region[]> {
  const out: Region[] = [];
  for (let page = 1; page <= 20; page++) {
    const r = await getPaged<Region>("regions/", { ...f, include_boundary: false, page, page_size: 200 });
    out.push(...r.items);
    if (!r.pagination || page >= r.pagination.total_pages) break;
  }
  return out;
}

/** Region polygons (GeoJSON geometry) for drawing areas that have no estimate. */
export async function getRegionBoundaries(f: { country: string; level: string }): Promise<Region[]> {
  const out: Region[] = [];
  for (let page = 1; page <= 20; page++) {
    const r = await getPaged<Region>("regions/", { ...f, include_boundary: true, page, page_size: 200 });
    out.push(...r.items);
    if (!r.pagination || page >= r.pagination.total_pages) break;
  }
  return out;
}

// ---- prevalence -----------------------------------------------------------
export const getPrevalence = (f: GeoFilter & { source_type?: string }) =>
  getPaged<PrevalenceEstimate>("prevalence/", { ...f });

export const getPrevalenceUncertainty = (f: GeoFilter) =>
  getPaged<PrevalenceUncertainty>("prevalence/uncertainty/", { ...f });

export const getPrevalenceMap = (f: { country?: string; year?: number | null; resolution?: string; source_type?: string }) =>
  getOne<PrevalenceMap>("prevalence/map/", { ...f });

// ---- other science domains ----------------------------------------------
export const getPopulationAtRisk = (f: GeoFilter) => getPaged<PopulationAtRisk>("population-at-risk/", { ...f });

export const getSpecies = (f: GeoFilter & { species?: string }) => getPaged<SpeciesRecord>("species/", { ...f });

export const getDrugEfficacy = (f: GeoFilter & { drug?: string; followup_days?: number | null; record_type?: string }) =>
  getPaged<DrugEfficacy>("drugs/efficacy/", { country: f.country, region_id: f.region_id, drug: f.drug,
    followup_days: f.followup_days, record_type: f.record_type });

export const getResistance = (f: GeoFilter & { marker?: string }) =>
  getPaged<ResistanceObservation>("resistance/", { ...f });

export const getResistanceTrends = (f: GeoFilter & { marker?: string }) =>
  getPaged<MarkerTrend>("resistance/trends/", { ...f });

// ---- environment ----------------------------------------------------------
/** Weather needs a region (with a loaded boundary) OR latitude+longitude - a country alone is rejected. */
export interface LocationFilter {
  country?: CountryCode | "";
  region_id?: number | null;
  latitude?: number | null;
  longitude?: number | null;
}

export const getCurrentWeather = (f: LocationFilter) => getOne<CurrentWeather>("environment/current/", { ...f });

export const getWeatherHistory = (f: LocationFilter & { start_date: string; end_date: string }) =>
  getOne<WeatherHistory>("environment/history/", { ...f });

// ---- assistant ------------------------------------------------------------
export async function createBrief(req: BriefRequest): Promise<Brief> {
  // region_id is sent as null for a country-wide brief (nullable in BriefRequestSerializer).
  const r = await api.post<Envelope<Brief>>("assistant/brief/", {
    country: req.country,
    region_id: req.region_id ?? null,
    question: req.question,
  });
  return unwrap(r.data);
}

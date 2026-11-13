/**
 * Display rules shared by every page.
 *  - Prevalence and marker frequencies arrive as FRACTIONS (0-1): multiply by 100 to show %.
 *  - Drug-efficacy fields arrive as PERCENT (0-100): never multiply again.
 *  - null / undefined / NaN is "not available" - it is never shown as 0.
 */
import type { RiskClass, SourceType, SpeciesRecordType } from "../types/api";

export const NOT_AVAILABLE = "Not available";

export function isMissing(v: unknown): v is null | undefined {
  return v === null || v === undefined || (typeof v === "number" && !Number.isFinite(v));
}

/** Fraction 0-1 -> "12.3%". */
export function fractionToPercent(v: number | null | undefined, digits = 1): string {
  if (isMissing(v)) return NOT_AVAILABLE;
  return `${(v * 100).toFixed(digits)}%`;
}

/** Already a percentage (0-100) -> "96.9%". */
export function percent(v: number | null | undefined, digits = 1): string {
  if (isMissing(v)) return NOT_AVAILABLE;
  return `${v.toFixed(digits)}%`;
}

/** Interval of fractions -> "3.0% - 62.9%"; partial or missing bounds -> not available. */
export function fractionInterval(lo: number | null | undefined, hi: number | null | undefined, digits = 1): string {
  if (isMissing(lo) || isMissing(hi)) return NOT_AVAILABLE;
  return `${(lo * 100).toFixed(digits)}% - ${(hi * 100).toFixed(digits)}%`;
}

export function percentInterval(lo: number | null | undefined, hi: number | null | undefined, digits = 1): string {
  if (isMissing(lo) || isMissing(hi)) return NOT_AVAILABLE;
  return `${lo.toFixed(digits)}% - ${hi.toFixed(digits)}%`;
}

export function integer(v: number | null | undefined): string {
  if (isMissing(v)) return NOT_AVAILABLE;
  return Math.round(v).toLocaleString("en-US");
}

export function decimal(v: number | null | undefined, digits = 1, unit = ""): string {
  if (isMissing(v)) return NOT_AVAILABLE;
  return `${v.toFixed(digits)}${unit}`;
}

export function compactPeople(v: number | null | undefined): string {
  if (isMissing(v)) return NOT_AVAILABLE;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)} million`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)} thousand`;
  return integer(v);
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return NOT_AVAILABLE;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export const RISK_CLASS_LABEL: Record<RiskClass, string> = {
  very_low: "Very low (PfPR below 1%)",
  low: "Low (1% to below 10%)",
  moderate: "Moderate (10% to below 35%)",
  high: "High (35% and above)",
};

export const RISK_CLASS_ORDER: RiskClass[] = ["very_low", "low", "moderate", "high"];

/** Sequential single-hue ramp (light = lower PfPR); the class is always also written out. */
export const RISK_FILL: Record<RiskClass, string> = {
  very_low: "#cde2fb", low: "#6da7ec", moderate: "#256abf", high: "#0d366b",
};

/** PfPR fraction -> risk class (lower bound inclusive), matching the ML pipeline. */
export function riskClassOf(fraction: number | null | undefined): RiskClass | null {
  if (isMissing(fraction)) return null;
  if (fraction < 0.01) return "very_low";
  if (fraction < 0.1) return "low";
  if (fraction < 0.35) return "moderate";
  return "high";
}

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  observed: "Observed",
  modelled: "Modelled estimate",
};

export const SPECIES_RECORD_LABEL: Record<SpeciesRecordType, string> = {
  survey: "Survey (with denominator)",
  presence_only: "Presence observation only",
  modelled: "Modelled distribution",
};

export const COUNTRY_NAME: Record<string, string> = { KEN: "Kenya", TZA: "Tanzania", ETH: "Ethiopia" };

export const MARKER_LABEL: Record<string, string> = {
  pfk13_validated: "pfkelch13 - WHO-validated mutations",
  pfk13_candidate: "pfkelch13 - candidate mutations",
  pfcrt_K76T: "pfcrt K76T",
  pfmdr1_CNV: "pfmdr1 copy-number amplification",
};

export function markerLabel(m: string): string {
  return MARKER_LABEL[m] ?? m;
}

import { useQuery } from "@tanstack/react-query";
import type { Feature, Geometry } from "geojson";
import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import { getPrevalenceMap, getRegionBoundaries } from "../api/endpoints";
import { SelectionBar } from "../components/SelectionBar";
import { Card, EmptyState, ErrorState, Loading, Notice, PageHeader } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { PrevalenceMapProperties } from "../types/api";
import { fractionInterval, fractionToPercent, RISK_CLASS_LABEL, RISK_CLASS_ORDER, RISK_FILL, riskClassOf } from "../utils/format";

const NO_DATA_FILL = "#e5e7eb";

const CENTER: Record<string, [number, number]> = { KEN: [0.2, 37.9], TZA: [-6.3, 34.8], ETH: [9.1, 40.5] };

function FitTo({ data }: { data: Feature[] }) {
  const map = useMap();
  useEffect(() => {
    if (!data.length) return;
    const b = L.geoJSON(data as never).getBounds();
    if (b.isValid()) map.fitBounds(b, { padding: [16, 16] });
  }, [data, map]);
  return null;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

export default function MapPage() {
  const sel = useSelection();
  const [sourceType, setSourceType] = useState<"modelled" | "observed">("modelled");
  const [year, setYear] = useState<number>(2020);

  const map = useQuery({
    queryKey: ["prevalence-map", sel.country, sel.level, sourceType, year],
    queryFn: () => getPrevalenceMap({ country: sel.country, resolution: sel.level, source_type: sourceType, year }),
  });
  const boundaries = useQuery({
    queryKey: ["boundaries", sel.country, sel.level],
    queryFn: () => getRegionBoundaries({ country: sel.country, level: sel.level }),
    staleTime: 60 * 60_000,
  });

  const features = useMemo(() => (map.data?.features ?? []).filter((f) => f.geometry), [map.data]);
  const noData = useMemo(() => {
    const have = new Set(features.map((f) => f.properties.region_id));
    return (boundaries.data ?? [])
      .filter((r) => r.boundary && !have.has(r.id))
      .map((r): Feature<Geometry, { name: string }> => ({
        type: "Feature", geometry: r.boundary as Geometry, properties: { name: r.name },
      }));
  }, [features, boundaries.data]);

  const layerKey = `${sel.country}-${sel.level}-${sourceType}-${year}-${features.length}-${noData.length}`;

  return (
    <>
      <PageHeader title="Geographic surveillance map"
        description="PfPR by administrative area. Areas without an estimate are shown in grey and labelled 'No estimate' - never as zero." />
      <SelectionBar />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Layer
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value as typeof sourceType)}
            className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
            <option value="modelled">Modelled PfPR (2-10 years)</option>
            <option value="observed">Observed survey prevalence</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Year
          <input type="number" min={1990} max={2030} value={year} onChange={(e) => setYear(Number(e.target.value) || 2020)}
            className="w-28 rounded-md border border-line bg-white px-2.5 py-1.5 text-sm" />
        </label>
        {map.data?.truncated && (
          <p className="text-xs text-amber-700">Showing {map.data.feature_count} of {map.data.total_matching} areas (server limit).</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
        <Card className="p-0 sm:p-0">
          <div className="relative h-[60vh] min-h-[360px] w-full overflow-hidden rounded-lg">
            {(map.isLoading || boundaries.isLoading) && (
              <div className="absolute inset-0 z-[500] flex items-center justify-center bg-white/70"><Loading label="Loading map layers..." /></div>
            )}
            <MapContainer center={CENTER[sel.country]} zoom={6} scrollWheelZoom className="h-full w-full">
              <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              {noData.length > 0 && (
                <GeoJSON key={`nd-${layerKey}`} data={{ type: "FeatureCollection", features: noData } as never}
                  style={() => ({ color: "#6b7480", weight: 0.8, dashArray: "3 3", fillColor: NO_DATA_FILL, fillOpacity: 0.6 })}
                  onEachFeature={(f, layer) => layer.bindPopup(
                    `<strong>${escapeHtml((f.properties as { name: string }).name)}</strong><br/>No estimate available for this layer and year.`)} />
              )}
              {features.length > 0 && (
                <GeoJSON key={`d-${layerKey}`} data={{ type: "FeatureCollection", features } as never}
                  style={(f) => {
                    const p = f?.properties as PrevalenceMapProperties;
                    const rc = riskClassOf(p.estimate);
                    return { color: "#ffffff", weight: 0.6, fillColor: rc ? RISK_FILL[rc] : NO_DATA_FILL, fillOpacity: 0.85 };
                  }}
                  onEachFeature={(f, layer) => {
                    const p = f.properties as PrevalenceMapProperties;
                    const rc = riskClassOf(p.estimate);
                    layer.bindPopup(
                      `<strong>${escapeHtml(p.region_name)}</strong> (${p.year})<br/>` +
                      `${p.source_type === "modelled" ? "Modelled estimate" : "Observed"} PfPR: <strong>${fractionToPercent(p.estimate)}</strong><br/>` +
                      `Interval: ${fractionInterval(p.lower_interval, p.upper_interval)}<br/>` +
                      `Class: ${rc ? RISK_CLASS_LABEL[rc] : "Not available"}<br/>` +
                      (p.model_version ? `Model version: ${escapeHtml(p.model_version)}<br/>` : "") +
                      `Evidence: ${p.evidence_ids.map(escapeHtml).join(", ") || "none"}`);
                  }} />
              )}
              <FitTo data={features.length ? features : noData} />
            </MapContainer>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Legend" subtitle={sourceType === "modelled" ? "Modelled PfPR, children 2-10" : "Observed survey prevalence"}>
            <ul className="space-y-1.5 text-xs">
              {RISK_CLASS_ORDER.map((rc) => (
                <li key={rc} className="flex items-center gap-2">
                  <span className="h-3.5 w-5 shrink-0 rounded-sm border border-line" style={{ background: RISK_FILL[rc] }} aria-hidden />
                  {RISK_CLASS_LABEL[rc]}
                </li>
              ))}
              <li className="flex items-center gap-2">
                <span className="h-3.5 w-5 shrink-0 rounded-sm border border-dashed border-ink-3" style={{ background: NO_DATA_FILL }} aria-hidden />
                No estimate (missing - not zero)
              </li>
            </ul>
          </Card>
          {map.isError && <ErrorState error={map.error} onRetry={() => map.refetch()} />}
          {!map.isLoading && !map.isError && features.length === 0 && (
            <EmptyState title="No areas with estimates" message="No prevalence estimates match this country, level, layer and year." />
          )}
          <Notice>
            Click an area for its estimate, interval and evidence. Modelled values are estimates, not measurements;
            see the Prevalence page for reliability flags. Synthetic data, if any, is labelled by its evidence source.
          </Notice>
          <p className="text-[11px] text-ink-3">Boundaries: geoBoundaries. Basemap: OpenStreetMap contributors.</p>
        </div>
      </div>
    </>
  );
}

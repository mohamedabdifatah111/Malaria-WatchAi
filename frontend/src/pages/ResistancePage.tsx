import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { getResistance, getResistanceTrends } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import { Card, DataTable, EmptyState, EvidenceIds, Notice, PageHeader, QueryView, type Column } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { ResistanceObservation } from "../types/api";
import { fractionInterval, fractionToPercent, integer, markerLabel, MARKER_LABEL } from "../utils/format";

export default function ResistancePage() {
  const sel = useSelection();
  const regions = useRegions(sel.country, "ADM1");
  const names = useMemo(() => new Map((regions.data ?? []).map((r) => [r.id, r.name])), [regions.data]);
  const [marker, setMarker] = useState("pfk13_validated");

  const obs = useQuery({
    queryKey: ["resistance", sel.country, sel.regionId, marker],
    queryFn: () => getResistance({ country: sel.country, region_id: sel.regionId, marker }),
  });
  const trends = useQuery({
    queryKey: ["resistance-trends", sel.country, marker],
    queryFn: () => getResistanceTrends({ country: sel.country, marker }),
  });

  const trendData = useMemo(() => (trends.data?.items ?? [])
    .filter((t) => t.region_id === null)
    .sort((a, b) => a.year - b.year)
    .map((t) => ({
      year: t.year,
      observed: t.observed_frequency === null ? null : +(t.observed_frequency * 100).toFixed(1),
      predicted: t.predicted_frequency === null ? null : +(t.predicted_frequency * 100).toFixed(1),
      n: t.n_tested,
    })), [trends.data]);
  const hasPredicted = trendData.some((d) => d.predicted !== null);

  const columns: Column<ResistanceObservation>[] = [
    { key: "r", header: "Area", render: (r) => (r.region_id ? names.get(r.region_id) ?? `Region ${r.region_id}` : "Country level") },
    { key: "y", header: "Year", render: (r) => r.year },
    { key: "n", header: "Tested", className: "text-right tabular-nums", render: (r) => integer(r.n_tested) },
    { key: "m", header: "Carrying marker", className: "text-right tabular-nums", render: (r) => integer(r.n_mutant) },
    { key: "f", header: "Frequency", className: "text-right tabular-nums", render: (r) => fractionToPercent(r.frequency) },
    { key: "ci", header: "95% CI", className: "tabular-nums", render: (r) => fractionInterval(r.confidence_interval_lower, r.confidence_interval_upper) },
    { key: "e", header: "Source", render: (r) => <EvidenceIds ids={r.evidence_ids} /> },
  ];

  return (
    <>
      <PageHeader title="Drug resistance markers"
        description="Molecular markers associated with reduced antimalarial susceptibility, with sample sizes and sources." />
      <SelectionBar showLevel={false} />
      <label className="mb-4 flex max-w-sm flex-col gap-1 text-xs font-medium text-ink-2">
        Marker
        <select value={marker} onChange={(e) => setMarker(e.target.value)} className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
          {Object.entries(MARKER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <Notice>
        A resistance marker is not proof of clinical treatment failure: a pfkelch13 signal can indicate partial artemisinin
        resistance but does not by itself show that a regimen fails. Samples come from few sites and may not represent a
        whole country.
      </Notice>

      <Card className="mt-4" title={`${markerLabel(marker)} - country trend`}
        subtitle="Observed frequency per year (points). Model trend shown only where the backend supplies one.">
        {trends.isLoading ? null : trendData.length === 0 ? (
          <EmptyState message="No trend records for this marker and country." />
        ) : (
          <div className="h-72 w-full" role="img" aria-label={`Observed ${markerLabel(marker)} frequency by year`}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trendData} margin={{ left: 4, right: 16 }}>
                <CartesianGrid vertical={false} stroke="#e3e6ea" />
                <XAxis dataKey="year" type="number" domain={["dataMin", "dataMax"]} allowDecimals={false} tick={{ fontSize: 11, fill: "#4a5563" }} />
                <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11, fill: "#4a5563" }} />
                <Tooltip formatter={(v, n) => [v === null ? "Not available" : `${v}%`, n === "observed" ? "Observed" : "Model trend"]}
                  labelFormatter={(y) => `Year ${y}`} />
                <Legend formatter={(v) => (v === "observed" ? "Observed frequency" : "Model trend (not recommended for decisions)")} wrapperStyle={{ fontSize: 11 }} />
                <Scatter dataKey="observed" fill="#0f766e" />
                {hasPredicted && <Line dataKey="predicted" stroke="#6b7480" strokeDasharray="4 3" dot={false} connectNulls />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
        {hasPredicted && (
          <p className="mt-2 text-xs text-ink-3">The trend model did not beat simple baselines in validation; prefer the latest observed frequency.</p>
        )}
      </Card>

      <Card className="mt-4" title="Observations" subtitle={`${obs.data?.items.length ?? 0} records`}>
        <QueryView query={obs} isEmpty={(d) => d.items.length === 0}
          empty={<EmptyState message={obs.data?.message ?? "No marker observations for this selection."} />}>
          {(d) => <DataTable rows={d.items} columns={columns} caption="Resistance marker observations"
            rowKey={(r, i) => `${r.region_id}-${r.year}-${r.source_id}-${i}`} />}
        </QueryView>
      </Card>
    </>
  );
}

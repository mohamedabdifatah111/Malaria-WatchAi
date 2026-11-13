import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getPrevalence, getPrevalenceUncertainty } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import {
  Badge, Card, DataTable, EmptyState, EvidenceIds, Notice, PageHeader, QueryView, SourceTypeBadge, type Column,
} from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { PrevalenceEstimate, PrevalenceUncertainty } from "../types/api";
import { decimal, fractionInterval, fractionToPercent } from "../utils/format";

type Row = PrevalenceEstimate & { unc?: PrevalenceUncertainty };

const RELIABILITY_TONE: Record<string, "observed" | "warning" | "critical" | "neutral"> = {
  ok: "observed", low: "warning", extrapolated: "critical",
};

export default function PrevalencePage() {
  const sel = useSelection();
  const [sourceType, setSourceType] = useState<"" | "modelled" | "observed">("modelled");
  const [year, setYear] = useState<string>("");
  const regions = useRegions(sel.country, sel.level);
  const filter = { country: sel.country, region_id: sel.regionId, year: year ? Number(year) : null };

  const prevalence = useQuery({
    queryKey: ["prevalence", filter, sourceType],
    queryFn: () => getPrevalence({ ...filter, source_type: sourceType }),
  });
  const uncertainty = useQuery({
    queryKey: ["prevalence-uncertainty", filter],
    queryFn: () => getPrevalenceUncertainty(filter),
    enabled: sourceType !== "observed",
  });

  const levelIds = useMemo(() => new Set((regions.data ?? []).map((r) => r.id)), [regions.data]);
  const rows: Row[] = useMemo(() => {
    const unc = new Map((uncertainty.data?.items ?? []).map((u) => [`${u.region_id}-${u.year}`, u]));
    return (prevalence.data?.items ?? [])
      .filter((r) => sel.regionId !== null || levelIds.size === 0 || levelIds.has(r.region_id))
      .map((r) => ({ ...r, unc: r.source_type === "modelled" ? unc.get(`${r.region_id}-${r.year}`) : undefined }));
  }, [prevalence.data, uncertainty.data, levelIds, sel.regionId]);

  const years = useMemo(() => [...new Set((prevalence.data?.items ?? []).map((r) => r.year))].sort((a, b) => b - a),
    [prevalence.data]);

  const chart = useMemo(() => rows
    .filter((r) => r.source_type === "modelled")
    .sort((a, b) => b.estimate - a.estimate)
    .slice(0, 15)
    .map((r) => ({
      name: r.region_name,
      pct: +(r.estimate * 100).toFixed(1),
      err: r.lower_interval !== null && r.upper_interval !== null
        ? [+((r.estimate - r.lower_interval) * 100).toFixed(1), +((r.upper_interval - r.estimate) * 100).toFixed(1)]
        : [0, 0],
    })), [rows]);

  const columns: Column<Row>[] = [
    { key: "region", header: "Region", render: (r) => <span className="font-medium">{r.region_name}</span> },
    { key: "year", header: "Year", render: (r) => r.year },
    { key: "type", header: "Type", render: (r) => <SourceTypeBadge type={r.source_type} /> },
    { key: "est", header: "PfPR", className: "text-right tabular-nums", render: (r) => fractionToPercent(r.estimate) },
    { key: "int", header: "Interval", className: "tabular-nums", render: (r) => fractionInterval(r.lower_interval, r.upper_interval) },
    { key: "rel", header: "Reliability", render: (r) => r.unc
        ? <Badge tone={RELIABILITY_TONE[r.unc.reliability_status] ?? "neutral"}>{r.unc.reliability_status || "not stated"}</Badge>
        : <span className="text-xs text-ink-3">-</span> },
    { key: "dist", header: "Nearest survey", className: "text-right tabular-nums",
      render: (r) => r.unc ? decimal(r.unc.nearest_survey_distance_km, 0, " km") : "-" },
    { key: "ev", header: "Evidence", render: (r) => <EvidenceIds ids={r.evidence_ids} /> },
  ];

  return (
    <>
      <PageHeader title="Prevalence analytics"
        description="Plasmodium falciparum parasite rate (PfPR). Modelled estimates are for children aged 2-10 by microscopy; observed values are pooled surveys as conducted (mixed ages and methods)." />
      <SelectionBar />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Data type
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value as typeof sourceType)}
            className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
            <option value="modelled">Modelled estimates</option>
            <option value="observed">Observed surveys</option>
            <option value="">Both (labelled)</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Year
          <select value={year} onChange={(e) => setYear(e.target.value)} className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
            <option value="">All years</option>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
      </div>

      <Notice>
        Modelled values are estimates, not measurements. Intervals are 90% model intervals (observed rows: 95% binomial
        intervals). Areas marked <strong>extrapolated</strong> are far from any survey or have conditions unlike surveyed places.
      </Notice>

      <div className="mt-4 grid gap-4">
        <Card title="Highest modelled PfPR" subtitle="Top 15 regions in the current selection, with interval (percent)">
          {prevalence.isLoading ? null : chart.length === 0 ? (
            <EmptyState title="No modelled estimates for this selection" />
          ) : (
            <div className="h-80 w-full" role="img" aria-label="Bar chart of modelled PfPR by region with intervals">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid horizontal={false} stroke="#e3e6ea" />
                  <XAxis type="number" unit="%" tick={{ fontSize: 11, fill: "#4a5563" }} />
                  <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: "#4a5563" }} />
                  <Tooltip formatter={(v) => [`${v}%`, "Modelled PfPR"]} />
                  <Bar dataKey="pct" fill="#1f4d78" radius={[0, 4, 4, 0]} barSize={14}>
                    <ErrorBar dataKey="err" direction="x" stroke="#6b7480" width={4} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Estimates" subtitle={`${rows.length} records`}>
          <QueryView query={prevalence} isEmpty={() => rows.length === 0}
            empty={<EmptyState message={prevalence.data?.message ?? "No validated prevalence records are available for this selection."} />}>
            {() => <DataTable rows={rows} columns={columns} caption="Prevalence estimates"
              rowKey={(r) => `${r.region_id}-${r.year}-${r.source_type}`} />}
          </QueryView>
        </Card>
      </div>
    </>
  );
}

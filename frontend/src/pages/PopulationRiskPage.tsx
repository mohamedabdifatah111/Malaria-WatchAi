import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getPopulationAtRisk } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import { Card, DataTable, EmptyState, EvidenceIds, Notice, PageHeader, QueryView, type Column } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { PopulationAtRisk, RiskClass } from "../types/api";
import { compactPeople, integer, RISK_CLASS_LABEL, RISK_CLASS_ORDER, RISK_FILL } from "../utils/format";

export default function PopulationRiskPage() {
  const sel = useSelection();
  const regions = useRegions(sel.country, sel.level);
  const names = useMemo(() => new Map((regions.data ?? []).map((r) => [r.id, r.name])), [regions.data]);
  const q = useQuery({
    queryKey: ["par", sel.country, sel.regionId],
    queryFn: () => getPopulationAtRisk({ country: sel.country, region_id: sel.regionId, year: 2020 }),
  });

  // Keep only regions at the selected level (rows for both ADM1 and ADM2 are returned).
  const rows = useMemo(() => (q.data?.items ?? []).filter((r) => sel.regionId !== null || names.size === 0 || names.has(r.region_id)),
    [q.data, names, sel.regionId]);

  const chart = useMemo(() => {
    const by = new Map<number, Record<string, number | string>>();
    for (const r of rows) {
      const e = by.get(r.region_id) ?? { name: names.get(r.region_id) ?? `Region ${r.region_id}`, total: 0 };
      e[r.risk_class] = r.population;
      e.total = (e.total as number) + r.population;
      by.set(r.region_id, e);
    }
    return [...by.values()].sort((a, b) => (b.total as number) - (a.total as number)).slice(0, 12);
  }, [rows, names]);

  const columns: Column<PopulationAtRisk>[] = [
    { key: "r", header: "Region", render: (r) => names.get(r.region_id) ?? `Region ${r.region_id}` },
    { key: "c", header: "PfPR class", render: (r) => RISK_CLASS_LABEL[r.risk_class] },
    { key: "p", header: "People living in class", className: "text-right tabular-nums", render: (r) => integer(r.population) },
    { key: "s", header: "Population source", render: (r) => <span className="text-xs">{r.population_source}</span> },
    { key: "m", header: "Model", render: (r) => <span className="text-xs">{r.prevalence_model_version}</span> },
    { key: "e", header: "Evidence", render: (r) => <EvidenceIds ids={r.evidence_ids} /> },
  ];

  return (
    <>
      <PageHeader title="Population at risk"
        description="People living where the modelled 2020 PfPR falls in each class. These are model-based estimates of exposure - not counts of infected people or confirmed cases." />
      <SelectionBar />
      <Notice>
        Method: WorldPop 2020 population on a 5 km grid, each cell assigned to the class of its modelled PfPR, summed by
        region. Interval-based scenarios are available in the ML outputs. National totals are not shown because the API
        holds regional rows only.
      </Notice>
      <Card className="mt-4" title="Largest regional populations by class" subtitle="Top 12 regions, people (model-based)">
        {q.isLoading ? null : chart.length === 0 ? (
          <EmptyState message="No validated population-at-risk estimates for this selection." />
        ) : (
          <div className="h-80 w-full" role="img" aria-label="Stacked bar chart of people living in each PfPR class by region">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} margin={{ left: 8, right: 8 }}>
                <CartesianGrid vertical={false} stroke="#e3e6ea" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#4a5563" }} interval={0} angle={-30} textAnchor="end" height={70} />
                <YAxis tickFormatter={(v: number) => compactPeople(v)} tick={{ fontSize: 10, fill: "#4a5563" }} width={90} />
                <Tooltip formatter={(v, n) => [integer(Number(v)), RISK_CLASS_LABEL[n as RiskClass] ?? n]} />
                <Legend formatter={(v) => RISK_CLASS_LABEL[v as RiskClass] ?? v} wrapperStyle={{ fontSize: 11 }} />
                {RISK_CLASS_ORDER.map((rc) => (
                  <Bar key={rc} dataKey={rc} stackId="a" fill={RISK_FILL[rc]} stroke="#fff" strokeWidth={1} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      <Card className="mt-4" title="Estimates" subtitle={`${rows.length} rows`}>
        <QueryView query={q} isEmpty={() => rows.length === 0}
          empty={<EmptyState message={q.data?.message ?? "No validated population-at-risk estimates for this selection."} />}>
          {() => <DataTable rows={rows} columns={columns} caption="Population at risk"
            rowKey={(r) => `${r.region_id}-${r.risk_class}`} />}
        </QueryView>
      </Card>
    </>
  );
}

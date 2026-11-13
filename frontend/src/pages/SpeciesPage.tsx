import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getSpecies } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import {
  Card, DataTable, EmptyState, EvidenceIds, Kpi, Notice, PageHeader, QueryView, SpeciesRecordBadge, type Column,
} from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { SpeciesName, SpeciesRecord } from "../types/api";
import { fractionToPercent, integer } from "../utils/format";

const SPECIES: SpeciesName[] = ["P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi"];

/**
 * Survey rows carry positive/examined and can show a positivity rate for that
 * species. Presence-only rows show that a species was recorded - never a share,
 * a prevalence or an abundance.
 */
export function surveyRate(r: SpeciesRecord): number | null {
  if (r.record_type !== "survey" || r.positive === null || r.examined === null || r.examined <= 0) return null;
  return r.positive / r.examined;
}

export default function SpeciesPage() {
  const sel = useSelection();
  const regions = useRegions(sel.country, sel.level);
  const regionName = useMemo(() => new Map((regions.data ?? []).map((r) => [r.id, r.name])), [regions.data]);
  const [species, setSpecies] = useState("");
  const q = useQuery({
    queryKey: ["species", sel.country, sel.regionId, species],
    queryFn: () => getSpecies({ country: sel.country, region_id: sel.regionId, species }),
  });
  const rows = q.data?.items ?? [];

  const summary = useMemo(() => SPECIES.map((sp) => {
    const r = rows.filter((x) => x.species === sp);
    return {
      species: sp,
      surveys: r.filter((x) => x.record_type === "survey").length,
      presence: r.filter((x) => x.record_type === "presence_only").length,
      years: r.length ? `${Math.min(...r.map((x) => x.year))}-${Math.max(...r.map((x) => x.year))}` : null,
    };
  }), [rows]);

  const columns: Column<SpeciesRecord>[] = [
    { key: "sp", header: "Species", render: (r) => <em>{r.species}</em> },
    { key: "type", header: "Record type", render: (r) => <SpeciesRecordBadge type={r.record_type} /> },
    { key: "where", header: "Area", render: (r) => r.region_id ? regionName.get(r.region_id) ?? `Region ${r.region_id}` : "Country level" },
    { key: "year", header: "Year", render: (r) => r.year },
    { key: "pos", header: "Positive / examined", className: "tabular-nums",
      render: (r) => r.record_type === "survey" ? `${integer(r.positive)} / ${integer(r.examined)}` : <span className="text-ink-3">Not applicable</span> },
    { key: "rate", header: "Survey positivity", className: "text-right tabular-nums",
      render: (r) => { const v = surveyRate(r); return v === null ? <span className="text-ink-3">-</span> : fractionToPercent(v); } },
    { key: "ev", header: "Evidence", render: (r) => <EvidenceIds ids={r.evidence_ids} /> },
  ];

  return (
    <>
      <PageHeader title="Species surveillance"
        description="Plasmodium species records. Survey records have denominators; presence observations only show that a species was recorded." />
      <SelectionBar />
      <label className="mb-4 flex max-w-xs flex-col gap-1 text-xs font-medium text-ink-2">
        Species
        <select value={species} onChange={(e) => setSpecies(e.target.value)} className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
          <option value="">All species</option>
          {SPECIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <Notice>
        Presence-only records (e.g. GBIF) cannot establish prevalence, abundance or a share of malaria cases, so no
        percentage is ever computed from them. Microscopy can miss low-density and mixed infections.
      </Notice>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {summary.map((s) => (
          <Kpi key={s.species} label={s.species}
            value={s.surveys + s.presence ? `${s.surveys + s.presence} records` : null}
            hint={s.surveys + s.presence ? `${s.surveys} survey · ${s.presence} presence-only · ${s.years}` : "No records for this selection"} />
        ))}
      </div>

      <Card className="mt-4" title="Records" subtitle={`${rows.length} records`}>
        <QueryView query={q} isEmpty={(d) => d.items.length === 0}
          empty={<EmptyState message={q.data?.message ?? "No species records for this selection."} />}>
          {(d) => <DataTable rows={d.items} columns={columns} caption="Species records"
            rowKey={(r, i) => `${r.species}-${r.region_id}-${r.year}-${r.record_type}-${i}`} />}
        </QueryView>
      </Card>
    </>
  );
}

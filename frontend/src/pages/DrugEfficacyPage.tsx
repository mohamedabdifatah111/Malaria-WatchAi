import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getDrugEfficacy } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import { Badge, Card, DataTable, EmptyState, EvidenceIds, Kpi, Notice, PageHeader, QueryView, type Column } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { DrugEfficacy } from "../types/api";
import { integer, percent, percentInterval } from "../utils/format";

const DRUGS = [
  { code: "AL", name: "Artemether-lumefantrine" },
  { code: "DHA-PPQ", name: "Dihydroartemisinin-piperaquine" },
  { code: "AS-AQ", name: "Artesunate-amodiaquine" },
];

/** Efficacy fields are already percentages (0-100) - shown as-is, never multiplied. */
export default function DrugEfficacyPage() {
  const sel = useSelection();
  const regions = useRegions(sel.country, "ADM1");
  const names = useMemo(() => new Map((regions.data ?? []).map((r) => [r.id, r.name])), [regions.data]);
  const [drug, setDrug] = useState("AL");
  const [followup, setFollowup] = useState(28);

  const q = useQuery({
    queryKey: ["efficacy", sel.country, drug, followup],
    queryFn: () => getDrugEfficacy({ country: sel.country, drug, followup_days: followup }),
  });
  const items = q.data?.items ?? [];
  const pooled = items.find((r) => r.record_type === "pooled");
  const studies = items.filter((r) => r.record_type === "study");

  const columns: Column<DrugEfficacy>[] = [
    { key: "site", header: "Study site", render: (r) => <span className="font-medium">{r.site || "Not stated"}</span> },
    { key: "region", header: "Region", render: (r) => (r.region_id ? names.get(r.region_id) ?? `Region ${r.region_id}` : "Not mapped") },
    { key: "yr", header: "Years", render: (r) => r.year_range },
    { key: "n", header: "Patients", className: "text-right tabular-nums", render: (r) => integer(r.n_patients) },
    { key: "acpr", header: "PCR-corrected ACPR", className: "text-right tabular-nums", render: (r) => percent(r.acpr_percent) },
    { key: "ci", header: "95% CI", className: "tabular-nums", render: (r) => percentInterval(r.confidence_interval_lower, r.confidence_interval_upper) },
    { key: "fail", header: "Failure", className: "text-right tabular-nums", render: (r) => percent(r.failure_percent) },
    { key: "ev", header: "Evidence", render: (r) => <EvidenceIds ids={r.evidence_ids} /> },
  ];

  const drugName = DRUGS.find((d) => d.code === drug)?.name ?? drug;
  return (
    <>
      <PageHeader title="Drug efficacy surveillance"
        description="Therapeutic efficacy studies of artemisinin-based combination therapies (PCR-corrected adequate clinical and parasitological response)." />
      <SelectionBar showLevel={false} />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Medicine
          <select value={drug} onChange={(e) => setDrug(e.target.value)} className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
            {DRUGS.map((d) => <option key={d.code} value={d.code}>{d.name} ({d.code})</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">
          Follow-up
          <select value={followup} onChange={(e) => setFollowup(Number(e.target.value))} className="rounded-md border border-line bg-white px-2.5 py-1.5 text-sm">
            <option value={28}>Day 28</option>
            <option value={42}>Day 42</option>
          </select>
        </label>
      </div>

      <Notice>
        Day-28 and day-42 results are never combined. Trial efficacy is not guaranteed real-world effectiveness. WHO's
        10% treatment-failure threshold signals a need for policy review - it is not a treatment recommendation. No
        individual treatment advice is given here.
      </Notice>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label={`Pooled ACPR, ${drug} day ${followup}`} value={pooled ? percent(pooled.acpr_percent) : null}
          hint={pooled ? `95% CI ${percentInterval(pooled.confidence_interval_lower, pooled.confidence_interval_upper)}` : "Fewer than 3 comparable studies, or none"}
          badge={pooled ? <Badge tone="modelled">Pooled estimate</Badge> : undefined} />
        <Kpi label="Studies pooled" value={pooled?.study_count ? String(pooled.study_count) : null}
          hint={pooled ? `${integer(pooled.n_patients)} patients · ${pooled.year_range}` : undefined} />
        <Kpi label="Prediction interval" value={pooled ? percentInterval(pooled.prediction_interval_lower, pooled.prediction_interval_upper) : null}
          hint="Range expected for a new study site" />
        <Kpi label="Heterogeneity (I²)" value={pooled ? percent(pooled.heterogeneity_i2, 0) : null}
          hint={pooled && pooled.failure_percent !== null && pooled.failure_percent >= 10
            ? "Pooled failure at or above the 10% review signal" : "Variation between study results"} />
      </div>

      <Card className="mt-4" title={`${drugName} studies, day ${followup}`} subtitle={`${studies.length} study records`}>
        <QueryView query={q} isEmpty={() => studies.length === 0}
          empty={<EmptyState title="No study records for this selection"
            message="Missing studies are not evidence of treatment success or failure." />}>
          {() => <DataTable rows={studies} columns={columns} caption="Therapeutic efficacy studies"
            rowKey={(r, i) => `${r.study_id ?? i}`} />}
        </QueryView>
      </Card>
    </>
  );
}

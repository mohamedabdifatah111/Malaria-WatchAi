import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { getDrugEfficacy, getPopulationAtRisk, getPrevalence, getPrevalenceUncertainty, getResistance, getSpecies } from "../api/endpoints";
import { SelectionBar, useRegions } from "../components/SelectionBar";
import { Badge, Card, ErrorState, Kpi, Notice, PageHeader } from "../components/ui";
import { useBriefHistory } from "../context/BriefHistoryContext";
import { useSelection } from "../context/SelectionContext";
import { COUNTRY_NAME, dateTime, fractionInterval, fractionToPercent, integer, percent, percentInterval, RISK_CLASS_LABEL } from "../utils/format";

function SectionLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1 text-xs font-medium text-teal-700 hover:underline">
      {label} <ArrowRight className="h-3 w-3" aria-hidden />
    </Link>
  );
}

export default function DashboardPage() {
  const sel = useSelection();
  const place = sel.regionName ?? COUNTRY_NAME[sel.country];
  const regions = useRegions(sel.country, sel.level);
  const levelIds = useMemo(() => new Set((regions.data ?? []).map((r) => r.id)), [regions.data]);
  const geo = { country: sel.country, region_id: sel.regionId };

  const prev = useQuery({ queryKey: ["prevalence", { ...geo, year: 2020 }, "modelled"],
    queryFn: () => getPrevalence({ ...geo, year: 2020, source_type: "modelled" }) });
  const unc = useQuery({ queryKey: ["prevalence-uncertainty", { ...geo, year: 2020 }],
    queryFn: () => getPrevalenceUncertainty({ ...geo, year: 2020 }) });
  const par = useQuery({ queryKey: ["par", sel.country, sel.regionId],
    queryFn: () => getPopulationAtRisk({ ...geo, year: 2020 }) });
  const species = useQuery({ queryKey: ["species", sel.country, sel.regionId, ""],
    queryFn: () => getSpecies(geo) });
  const eff = useQuery({ queryKey: ["efficacy", sel.country, "AL", 28],
    queryFn: () => getDrugEfficacy({ country: sel.country, drug: "AL", followup_days: 28 }) });
  const res = useQuery({ queryKey: ["resistance", sel.country, sel.regionId, "pfk13_validated"],
    queryFn: () => getResistance({ ...geo, marker: "pfk13_validated" }) });
  const { briefs } = useBriefHistory();

  const prevRows = (prev.data?.items ?? []).filter((r) => sel.regionId !== null || levelIds.has(r.region_id));
  const regionEstimate = sel.regionId ? prevRows.find((r) => r.region_id === sel.regionId) : undefined;
  const uncRows = (unc.data?.items ?? []).filter((r) => sel.regionId !== null || levelIds.has(r.region_id));
  const extrapolated = uncRows.filter((u) => u.reliability_status === "extrapolated").length;
  const parRows = (par.data?.items ?? []).filter((r) => (sel.regionId ? r.region_id === sel.regionId : false));
  const largestClass = [...parRows].sort((a, b) => b.population - a.population)[0];
  const pooled = eff.data?.items.find((r) => r.record_type === "pooled");
  const spRows = species.data?.items ?? [];
  const resRows = res.data?.items ?? [];
  const latestRes = [...resRows].sort((a, b) => b.year - a.year)[0];

  const anyError = [prev, par, species, eff, res].find((q) => q.isError);

  return (
    <>
      <PageHeader title="Surveillance overview" description={`Evidence available for ${place}. Values are shown only when the API returns them.`} />
      <SelectionBar />
      {anyError && <div className="mb-4"><ErrorState error={anyError.error} onRetry={() => anyError.refetch()} /></div>}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {sel.regionId ? (
          <Kpi label={`Modelled PfPR 2020 · ${place}`} value={regionEstimate ? fractionToPercent(regionEstimate.estimate) : null}
            hint={regionEstimate ? `Interval ${fractionInterval(regionEstimate.lower_interval, regionEstimate.upper_interval)} · children 2-10` : "No modelled estimate for this region"}
            badge={regionEstimate ? <Badge tone="modelled">Modelled</Badge> : undefined} />
        ) : (
          <Kpi label={`Areas with a 2020 modelled estimate (${sel.level})`} value={prev.isLoading ? null : String(prevRows.length)}
            hint={uncRows.length ? `${extrapolated} of ${uncRows.length} flagged as extrapolated` : "Select a region for its estimate"} />
        )}
        <Kpi label="Pooled AL efficacy, day 28" value={pooled ? percent(pooled.acpr_percent) : null}
          hint={pooled ? `95% CI ${percentInterval(pooled.confidence_interval_lower, pooled.confidence_interval_upper)} · ${pooled.study_count} studies` : "Insufficient comparable studies"}
          badge={pooled ? <Badge tone="modelled">Pooled</Badge> : undefined} />
        <Kpi label="WHO-validated pfkelch13, latest year" value={latestRes ? `${integer(latestRes.n_mutant)} of ${integer(latestRes.n_tested)}` : null}
          hint={latestRes ? `${latestRes.year} · samples carrying a validated marker · not treatment failure` : "No marker data for this selection"} />
        <Kpi label="Survey locations" value={null} hint="Endpoint not yet available in the API" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Population at risk" subtitle="People living in each modelled PfPR class - not infections" action={<SectionLink to="/population-risk" label="Details" />}>
          {!sel.regionId ? <p className="text-sm text-ink-2">Select a region to see how many people live in each class.</p>
            : largestClass ? (
              <ul className="space-y-1 text-sm">
                {[...parRows].sort((a, b) => b.population - a.population).map((r) => (
                  <li key={r.risk_class} className="flex justify-between gap-3"><span className="text-ink-2">{RISK_CLASS_LABEL[r.risk_class]}</span>
                    <span className="tabular-nums font-medium">{integer(r.population)}</span></li>
                ))}
              </ul>
            ) : <p className="text-sm text-ink-2">No validated population-at-risk estimate for this region.</p>}
        </Card>

        <Card title="Species evidence" subtitle="Record counts by type" action={<SectionLink to="/species" label="Details" />}>
          {spRows.length === 0 ? <p className="text-sm text-ink-2">No species records for this selection.</p> : (
            <ul className="space-y-1 text-sm">
              {["P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi"].map((sp) => {
                const r = spRows.filter((x) => x.species === sp);
                return (
                  <li key={sp} className="flex justify-between gap-3"><em className="text-ink-2">{sp}</em>
                    <span className="text-xs text-ink-2">{r.length ? `${r.filter((x) => x.record_type === "survey").length} survey · ${r.filter((x) => x.record_type === "presence_only").length} presence-only` : "No records"}</span></li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card title="Environment" subtitle="Weather context (not a risk score)" action={<SectionLink to="/environment" label="Open" />}>
          <p className="text-sm text-ink-2">Current and recent weather is retrieved for a selected region or coordinates on the Environment page.</p>
        </Card>

        <Card title="Recent surveillance briefs" subtitle="Generated in this browser session" action={<SectionLink to="/briefs" label="All briefs" />}>
          {briefs.length === 0 ? <p className="text-sm text-ink-2">No briefs generated yet. Use the AI assistant to create one.</p> : (
            <ul className="space-y-2 text-sm">
              {briefs.slice(0, 4).map((b) => (
                <li key={b.brief_id} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="min-w-0 truncate">{COUNTRY_NAME[b.country]}{b.region_id ? ` · region ${b.region_id}` : ""}</span>
                  <span className="text-xs text-ink-3">{b.status} · {dateTime(b.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="mt-4">
        <Notice>
          Modelled estimates are not observed measurements, and some areas are far from recent surveys (see the
          reliability flags and the model card). Every number links to an evidence identifier on its detail page.
        </Notice>
      </div>
    </>
  );
}

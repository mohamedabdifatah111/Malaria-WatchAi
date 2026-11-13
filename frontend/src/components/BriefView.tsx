import { AlertCircle, Info, ShieldCheck } from "lucide-react";
import type { Brief, BriefFinding, BriefStatus } from "../types/api";
import { COUNTRY_NAME, dateTime } from "../utils/format";
import { Badge, EvidenceIds } from "./ui";

const STATUS: Record<BriefStatus, { label: string; tone: "warning" | "observed" | "critical" | "neutral" }> = {
  draft: { label: "Draft - awaiting human review", tone: "warning" },
  edited: { label: "Edited - awaiting approval", tone: "warning" },
  approved: { label: "Approved", tone: "observed" },
  rejected: { label: "Rejected", tone: "critical" },
};

/**
 * Findings arrive from the backend as { topic, statement, evidence_ids }
 * (services/brief_builder.py). The frontend brief described { text }; both are
 * accepted so neither shape renders as "[object Object]".
 */
export function findingText(f: BriefFinding | string): string {
  if (typeof f === "string") return f;
  return f.statement ?? f.text ?? "";
}

export function BriefView({ brief, regionName }: { brief: Brief; regionName?: string | null }) {
  const status = STATUS[brief.status] ?? { label: brief.status, tone: "neutral" as const };
  const usesGemini = brief.limitations.some((l) => l.toLowerCase().includes("gemini"));
  return (
    <article className="space-y-4">
      <header className="flex flex-wrap items-center gap-2 text-xs text-ink-2">
        <Badge tone={status.tone}>{status.label}</Badge>
        <span>{COUNTRY_NAME[brief.country] ?? brief.country}{regionName ? ` · ${regionName}` : brief.region_id ? ` · region ${brief.region_id}` : " · country level"}</span>
        <span aria-hidden>·</span>
        <span>{dateTime(brief.created_at)}</span>
        {usesGemini && <Badge tone="modelled" title="Summary drafted by Google Gemini from the findings; numbers checked">AI-drafted summary</Badge>}
      </header>

      <section>
        <h3 className="text-sm font-semibold text-navy-900">Summary</h3>
        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-ink">{brief.summary}</p>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-navy-900">Findings</h3>
        {brief.findings.length === 0 ? (
          <p className="mt-1 text-sm text-ink-2">No validated findings were available for this area.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {brief.findings.map((f, i) => (
              <li key={i} className="rounded-md border border-line p-3 text-sm">
                {typeof f !== "string" && f.topic && (
                  <p className="mb-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-3">{f.topic}</p>
                )}
                <p className="text-ink">{findingText(f)}</p>
                {typeof f !== "string" && <div className="mt-1.5"><EvidenceIds ids={f.evidence_ids} /></div>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {brief.uncertainties.length > 0 && (
        <section>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-navy-900">
            <AlertCircle className="h-4 w-4 text-amber-700" aria-hidden /> Missing or partial evidence
          </h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink-2">
            {brief.uncertainties.map((u, i) => <li key={i}>{u}</li>)}
          </ul>
        </section>
      )}

      <section>
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-navy-900">
          <Info className="h-4 w-4 text-ink-3" aria-hidden /> Limitations
        </h3>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink-2">
          {brief.limitations.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </section>

      <footer className="flex flex-col gap-1 border-t border-line pt-3 text-xs text-ink-3">
        <span className="flex flex-wrap items-center gap-1">Evidence cited: <EvidenceIds ids={brief.evidence_ids} /></span>
        <span>Trace id: <code>{brief.tool_trace_id}</code></span>
        {brief.review && (
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Reviewed: {brief.review.decision}
            {brief.review.reviewer ? ` by ${brief.review.reviewer}` : ""} on {dateTime(brief.review.reviewed_at)}
          </span>
        )}
      </footer>
    </article>
  );
}

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toApiError } from "../api/client";
import { createBrief } from "../api/endpoints";
import { useBriefHistory } from "../context/BriefHistoryContext";
import { useSelection } from "../context/SelectionContext";
import type { Brief } from "../types/api";
import { COUNTRY_NAME } from "../utils/format";

export const PRESET_QUESTIONS = [
  "Summarise the available malaria surveillance evidence for this area.",
  "Explain the prevalence estimates and their uncertainty for this area.",
  "Summarise the species observations available for this area.",
  "Summarise the antimalarial drug efficacy evidence for this country.",
  "Summarise the resistance marker evidence and its limitations.",
];

/** Payload rule: region_id is null for a country-wide brief, the region's id otherwise. */
export function briefPayload(country: Brief["country"], regionId: number | null, question: string) {
  return { country, region_id: regionId ?? null, question: question.trim() };
}

export function BriefForm({ onCreated, compact = false }: { onCreated: (b: Brief) => void; compact?: boolean }) {
  const sel = useSelection();
  const history = useBriefHistory();
  const [question, setQuestion] = useState(PRESET_QUESTIONS[0]);
  const [regionWide, setRegionWide] = useState(true);
  const regionId = regionWide ? sel.regionId : null;

  const m = useMutation({
    mutationFn: () => createBrief(briefPayload(sel.country, regionId, question)),
    onSuccess: (b) => {
      history.add(b);
      onCreated(b);
    },
  });
  const err = m.isError ? toApiError(m.error) : null;
  const tooShort = question.trim().length < 3;

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!tooShort && !m.isPending) m.mutate();
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className="text-sm text-ink-2">
        Scope: <strong className="text-ink">{COUNTRY_NAME[sel.country]}</strong>
        {sel.regionId && regionWide ? <> · <strong className="text-ink">{sel.regionName}</strong></> : " · country-wide"}
      </p>
      {sel.regionId && (
        <label className="flex items-center gap-2 text-sm text-ink-2">
          <input type="checkbox" checked={regionWide} onChange={(e) => setRegionWide(e.target.checked)} />
          Limit to {sel.regionName}
        </label>
      )}
      {!compact && (
        <div className="flex flex-wrap gap-1.5">
          {PRESET_QUESTIONS.map((q) => (
            <button key={q} type="button" onClick={() => setQuestion(q)}
              className={`rounded-full border px-2.5 py-1 text-xs ${q === question ? "border-teal-600 bg-teal-50 text-teal-700" : "border-line bg-white text-ink-2 hover:bg-canvas"}`}>
              {q.replace(" for this area.", "").replace(" for this country.", "").replace("Summarise the ", "").replace("Explain the ", "")}
            </button>
          ))}
        </div>
      )}
      <label className="block text-sm font-medium text-ink" htmlFor="question">Question</label>
      <textarea id="question" rows={3} maxLength={500} value={question} onChange={(e) => setQuestion(e.target.value)}
        className="w-full rounded-md border border-line p-2.5 text-sm focus:border-teal-600" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-ink-3">Surveillance questions only - no diagnosis, dosing or treatment advice. {question.length}/500</p>
        <button type="submit" disabled={m.isPending || tooShort}
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600 disabled:opacity-60">
          {m.isPending ? "Generating brief..." : "Generate brief"}
        </button>
      </div>
      {err && (
        <p role="alert" className="rounded-md border border-crit-700/25 bg-crit-50 p-3 text-sm text-crit-700">
          {err.status === 422 || err.code.toLowerCase().includes("guardrail")
            ? `This request was refused: ${err.message}`
            : err.status === 429 ? "Too many requests. Wait a minute and try again." : err.message}
        </p>
      )}
    </form>
  );
}

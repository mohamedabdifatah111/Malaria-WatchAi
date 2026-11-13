import { useState } from "react";
import { BriefForm } from "../components/BriefForm";
import { BriefView } from "../components/BriefView";
import { SelectionBar } from "../components/SelectionBar";
import { Badge, Card, EmptyState, Notice, PageHeader } from "../components/ui";
import { useBriefHistory } from "../context/BriefHistoryContext";
import { COUNTRY_NAME, dateTime } from "../utils/format";

export default function BriefsPage() {
  const { briefs, clear } = useBriefHistory();
  const [selectedId, setSelectedId] = useState<string | null>(briefs[0]?.brief_id ?? null);
  const selected = briefs.find((b) => b.brief_id === selectedId) ?? null;

  return (
    <>
      <PageHeader title="Surveillance briefs"
        description="Generate country-wide or regional briefs and review their findings, evidence and limitations." />
      <SelectionBar />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="space-y-4">
          <Card title="Generate a brief"><BriefForm compact onCreated={(b) => setSelectedId(b.brief_id)} /></Card>
          <Card title="History" subtitle="Briefs generated in this browser session"
            action={briefs.length > 0 ? (
              <button type="button" onClick={() => { clear(); setSelectedId(null); }} className="text-xs text-ink-3 hover:text-ink">Clear</button>
            ) : undefined}>
            {briefs.length === 0 ? <EmptyState title="No briefs yet" message="Generated briefs will be listed here for this session." /> : (
              <ul className="divide-y divide-line">
                {briefs.map((b) => (
                  <li key={b.brief_id}>
                    <button type="button" onClick={() => setSelectedId(b.brief_id)} aria-current={b.brief_id === selectedId}
                      className={`flex w-full flex-col gap-1 px-2 py-2 text-left text-sm hover:bg-canvas ${b.brief_id === selectedId ? "bg-teal-50" : ""}`}>
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium">{COUNTRY_NAME[b.country]}{b.region_id ? ` · region ${b.region_id}` : " · country-wide"}</span>
                        <Badge tone={b.status === "approved" ? "observed" : b.status === "rejected" ? "critical" : "warning"}>{b.status}</Badge>
                      </span>
                      <span className="text-xs text-ink-3">{dateTime(b.created_at)} · {b.findings.length} findings</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Notice>
            A server-side brief list is not yet available in the API, so history covers this browser session only.
            Approval is restricted to authorised reviewers and is not enabled in this interface yet.
          </Notice>
        </div>
        <Card title="Brief details">
          {selected ? <BriefView brief={selected} /> : <p className="text-sm text-ink-2">Select or generate a brief.</p>}
        </Card>
      </div>
    </>
  );
}

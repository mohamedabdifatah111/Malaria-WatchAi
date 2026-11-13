import { useState } from "react";
import { BriefForm } from "../components/BriefForm";
import { BriefView } from "../components/BriefView";
import { SelectionBar } from "../components/SelectionBar";
import { Card, Notice, PageHeader } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import type { Brief } from "../types/api";

/**
 * The assistant is the backend's /assistant/brief/ endpoint: tools retrieve stored
 * evidence, every finding cites an evidence id, and Google Gemini may draft the
 * summary (number-checked on the server). Nothing is generated in the browser.
 */
export default function AssistantPage() {
  const sel = useSelection();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [briefRegion, setBriefRegion] = useState<string | null>(null);
  return (
    <>
      <PageHeader title="AI surveillance assistant"
        description="Ask a surveillance question. Answers are compiled by the backend from stored, cited evidence and returned as a draft brief for human review." />
      <SelectionBar />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Card title="Ask">
          <BriefForm onCreated={(b) => { setBrief(b); setBriefRegion(b.region_id ? sel.regionName : null); }} />
          <div className="mt-4">
            <Notice>
              The assistant does not diagnose patients, prescribe medicines or give dosages, and it does not invent
              statistics. When evidence is missing it says so. Drafts must be reviewed before they are approved.
            </Notice>
          </div>
        </Card>
        <Card title="Response" subtitle={brief ? undefined : "The generated brief will appear here"}>
          {brief ? <BriefView brief={brief} regionName={briefRegion} />
            : <p className="text-sm text-ink-2">No response yet.</p>}
        </Card>
      </div>
    </>
  );
}

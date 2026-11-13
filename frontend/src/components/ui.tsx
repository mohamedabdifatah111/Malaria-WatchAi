import { AlertTriangle, Info, Loader2, Lock, SearchX } from "lucide-react";
import type { ReactNode } from "react";
import type { ApiError } from "../api/client";
import type { SourceType, SpeciesRecordType } from "../types/api";
import { NOT_AVAILABLE, SOURCE_TYPE_LABEL, SPECIES_RECORD_LABEL } from "../utils/format";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, subtitle, children, className = "", action }: {
  title?: string; subtitle?: string; children: ReactNode; className?: string; action?: ReactNode;
}) {
  return (
    <section className={`min-w-0 rounded-lg border border-line bg-white p-4 shadow-[0_1px_2px_rgba(16,24,40,0.04)] sm:p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-navy-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

type Tone = "observed" | "modelled" | "presence" | "neutral" | "warning" | "critical" | "synthetic";
const TONE: Record<Tone, string> = {
  observed: "bg-teal-50 text-teal-700 border-teal-600/30",
  modelled: "bg-[#eef2fb] text-navy-700 border-navy-700/25",
  presence: "bg-moss-50 text-moss-600 border-moss-600/30",
  neutral: "bg-canvas text-ink-2 border-line",
  warning: "bg-amber-50 text-amber-700 border-amber-700/30",
  critical: "bg-crit-50 text-crit-700 border-crit-700/30",
  synthetic: "bg-[#f6f0fb] text-[#6b3fa0] border-[#6b3fa0]/30",
};

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] font-medium ${TONE[tone]}`}>
      {children}
    </span>
  );
}

/** Observed vs modelled, always in words (never colour alone). */
export function SourceTypeBadge({ type }: { type: SourceType | string }) {
  const tone: Tone = type === "observed" ? "observed" : type === "modelled" ? "modelled" : "neutral";
  return <Badge tone={tone}>{SOURCE_TYPE_LABEL[type as SourceType] ?? type}</Badge>;
}

export function SpeciesRecordBadge({ type }: { type: SpeciesRecordType }) {
  const tone: Tone = type === "presence_only" ? "presence" : type === "survey" ? "observed" : "modelled";
  return <Badge tone={tone}>{SPECIES_RECORD_LABEL[type] ?? type}</Badge>;
}

export function Loading({ label = "Loading data..." }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-sm text-ink-2">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function EmptyState({ title = "No validated data available", message }: { title?: string; message?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-dashed border-line bg-canvas/60 p-4 text-sm">
      <SearchX className="mt-0.5 h-4 w-4 shrink-0 text-ink-3" aria-hidden />
      <div>
        <p className="font-medium text-ink">{title}</p>
        {message && <p className="mt-0.5 text-ink-2">{message}</p>}
      </div>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const e = error as Partial<ApiError> | undefined;
  if (e?.status === 403) {
    return (
      <div className="flex items-start gap-3 rounded-md border border-line bg-canvas p-4 text-sm">
        <Lock className="mt-0.5 h-4 w-4 shrink-0 text-ink-3" aria-hidden />
        <p className="text-ink-2">This information requires reviewer permission, which your account does not have.</p>
      </div>
    );
  }
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md border border-crit-700/25 bg-crit-50 p-4 text-sm">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-crit-700" aria-hidden />
      <div className="min-w-0">
        <p className="font-medium text-crit-700">The data could not be loaded.</p>
        <p className="mt-0.5 break-words text-ink-2">{e?.message ?? "Unexpected error."}</p>
        {onRetry && (
          <button type="button" onClick={onRetry} className="mt-2 rounded border border-line bg-white px-2.5 py-1 text-xs font-medium text-ink hover:bg-canvas">
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warning" }) {
  const cls = tone === "warning" ? "border-amber-700/25 bg-amber-50 text-amber-700" : "border-navy-700/15 bg-[#f3f6fb] text-navy-800";
  return (
    <div className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs leading-relaxed ${cls}`}>
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

/** A KPI only shows a number when the API returned one; otherwise it says so. */
export function Kpi({ label, value, hint, badge }: { label: string; value: string | null; hint?: string; badge?: ReactNode }) {
  const missing = value === null || value === NOT_AVAILABLE;
  return (
    <div className="min-w-0 rounded-lg border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-ink-2">{label}</p>
        {badge}
      </div>
      <p className={`mt-2 truncate ${missing ? "text-sm font-medium text-ink-3" : "text-2xl font-semibold text-navy-900"}`}>
        {missing ? "Not available" : value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-3">{hint}</p>}
    </div>
  );
}

export function EvidenceIds({ ids }: { ids?: string[] | null }) {
  if (!ids?.length) return <span className="text-xs text-ink-3">No evidence reference</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {ids.map((id) => (
        <code key={id} className="rounded bg-canvas px-1 py-0.5 text-[11px] text-ink-2">{id}</code>
      ))}
    </span>
  );
}

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

/** Horizontally scrollable on small screens so the page itself never overflows. */
export function DataTable<T>({ rows, columns, caption, rowKey, max = 200 }: {
  rows: T[]; columns: Column<T>[]; caption: string; rowKey: (row: T, i: number) => string; max?: number;
}) {
  const shown = rows.slice(0, max);
  return (
    <div className="-mx-4 overflow-x-auto sm:mx-0">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-xs text-ink-2">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={`px-3 py-2 font-medium ${c.className ?? ""}`}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr key={rowKey(row, i)} className="border-b border-line/70 last:border-0 hover:bg-canvas/60">
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-2 align-top ${c.className ?? ""}`}>{c.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > max && <p className="px-3 pt-2 text-xs text-ink-3">Showing {max} of {rows.length} records.</p>}
    </div>
  );
}

/** Standard wrapper: loading -> error -> empty -> content. */
export function QueryView<T>({ query, isEmpty, empty, children, loadingLabel }: {
  query: { isLoading: boolean; isError: boolean; error: unknown; data: T | undefined; refetch: () => unknown };
  isEmpty: (d: T) => boolean;
  empty: ReactNode;
  children: (d: T) => ReactNode;
  loadingLabel?: string;
}) {
  if (query.isLoading) return <Loading label={loadingLabel} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (query.data === undefined || isEmpty(query.data)) return <>{empty}</>;
  return <>{children(query.data)}</>;
}

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { Brief } from "../types/api";

/**
 * The backend has no "list briefs" endpoint (only POST /assistant/brief/ and the
 * reviewer-only GET /assistant/logs/). Until one exists, history is the briefs
 * generated in this browser session. Stored in sessionStorage: cleared on sign-out
 * of the tab, never sent anywhere.
 */
const KEY = "mwai.briefs";
const MAX = 30;

interface BriefHistoryState {
  briefs: Brief[];
  add: (b: Brief) => void;
  clear: () => void;
}

const Ctx = createContext<BriefHistoryState | null>(null);

function load(): Brief[] {
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? (v as Brief[]) : [];
  } catch {
    return [];
  }
}

export function BriefHistoryProvider({ children }: { children: ReactNode }) {
  const [briefs, setBriefs] = useState<Brief[]>(load);
  const value = useMemo<BriefHistoryState>(() => ({
    briefs,
    add: (b) => setBriefs((prev) => {
      const next = [b, ...prev.filter((x) => x.brief_id !== b.brief_id)].slice(0, MAX);
      try { sessionStorage.setItem(KEY, JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    }),
    clear: () => {
      try { sessionStorage.removeItem(KEY); } catch { /* ignore */ }
      setBriefs([]);
    },
  }), [briefs]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useBriefHistory(): BriefHistoryState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useBriefHistory must be used inside BriefHistoryProvider");
  return ctx;
}

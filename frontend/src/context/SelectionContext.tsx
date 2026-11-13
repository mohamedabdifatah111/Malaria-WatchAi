import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { AdminLevel, CountryCode } from "../types/api";

export interface Selection {
  country: CountryCode;
  regionId: number | null;
  regionName: string | null;
  level: AdminLevel;
}

interface SelectionState extends Selection {
  setCountry: (c: CountryCode) => void;
  setRegion: (id: number | null, name: string | null) => void;
  setLevel: (l: AdminLevel) => void;
}

const KEY = "mwai.selection";
const DEFAULT: Selection = { country: "KEN", regionId: null, regionName: null, level: "ADM1" };

function load(): Selection {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) ?? "null") as Partial<Selection> | null;
    if (s && (s.country === "KEN" || s.country === "TZA" || s.country === "ETH")) return { ...DEFAULT, ...s };
  } catch {
    /* ignore - storage blocked or malformed */
  }
  return DEFAULT;
}

function save(s: Selection) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}

const SelectionContext = createContext<SelectionState | null>(null);

/** Country / region chosen once and shared by every page (remembered per browser). */
export function SelectionProvider({ children }: { children: ReactNode }) {
  const [sel, setSel] = useState<Selection>(load);
  const update = (next: Selection) => {
    setSel(next);
    save(next);
  };
  const value = useMemo<SelectionState>(() => ({
    ...sel,
    setCountry: (country) => update({ ...sel, country, regionId: null, regionName: null }),
    setRegion: (regionId, regionName) => update({ ...sel, regionId, regionName }),
    setLevel: (level) => update({ ...sel, level, regionId: null, regionName: null }),
  }), [sel]);
  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>;
}

export function useSelection(): SelectionState {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used inside SelectionProvider");
  return ctx;
}

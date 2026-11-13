import { useQuery } from "@tanstack/react-query";
import { getCountries, getRegions } from "../api/endpoints";
import { useSelection } from "../context/SelectionContext";
import type { AdminLevel, CountryCode } from "../types/api";

const selectCls =
  "w-full min-w-0 rounded-md border border-line bg-white px-2.5 py-1.5 text-sm text-ink focus:border-teal-600 sm:w-auto";

export function useRegions(country: string, level: AdminLevel) {
  return useQuery({
    queryKey: ["regions", country, level],
    queryFn: () => getRegions({ country, level }),
    staleTime: 30 * 60_000,
  });
}

/** Country + administrative level + region selectors used on every data page. */
export function SelectionBar({ showLevel = true }: { showLevel?: boolean }) {
  const sel = useSelection();
  const countries = useQuery({ queryKey: ["countries"], queryFn: getCountries, staleTime: 60 * 60_000 });
  const regions = useRegions(sel.country, sel.level);
  const regionList = [...(regions.data ?? [])].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="mb-5 flex flex-col gap-2 rounded-lg border border-line bg-white p-3 sm:flex-row sm:flex-wrap sm:items-end">
      <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-2">
        Country
        <select className={selectCls} value={sel.country}
          onChange={(e) => sel.setCountry(e.target.value as CountryCode)}>
          {(countries.data?.length ? countries.data : [
            { code: "KEN", name: "Kenya" }, { code: "TZA", name: "Tanzania" }, { code: "ETH", name: "Ethiopia" },
          ]).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
      </label>
      {showLevel && (
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-2">
          Administrative level
          <select className={selectCls} value={sel.level} onChange={(e) => sel.setLevel(e.target.value as AdminLevel)}>
            <option value="ADM1">Region / county / zone (ADM1)</option>
            <option value="ADM2">District / sub-county (ADM2)</option>
          </select>
        </label>
      )}
      <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-2 sm:min-w-56">
        Region
        <select className={selectCls} value={sel.regionId ?? ""} disabled={regions.isLoading}
          onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : null;
            sel.setRegion(id, regionList.find((r) => r.id === id)?.name ?? null);
          }}>
          <option value="">All of {sel.country === "KEN" ? "Kenya" : sel.country === "TZA" ? "Tanzania" : "Ethiopia"}</option>
          {regionList.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </label>
      <p className="text-xs text-ink-3 sm:ml-auto sm:self-center">
        {regions.isError ? "Regions could not be loaded."
          : regions.isLoading ? "Loading regions..."
          : regions.data && regions.data.length === 0 ? "No regions imported for this country and level."
          : `${regions.data?.length ?? 0} regions`}
      </p>
    </div>
  );
}

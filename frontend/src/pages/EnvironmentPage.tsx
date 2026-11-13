import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getCurrentWeather, getWeatherHistory } from "../api/endpoints";
import { SelectionBar } from "../components/SelectionBar";
import { Card, EmptyState, ErrorState, Kpi, Loading, Notice, PageHeader } from "../components/ui";
import { useSelection } from "../context/SelectionContext";
import { dateTime, decimal, isoDate } from "../utils/format";

export default function EnvironmentPage() {
  const sel = useSelection();
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [days, setDays] = useState(30);

  // The backend needs a region (with a loaded boundary) or a coordinate pair.
  const coords = lat !== "" && lon !== "" && Number.isFinite(+lat) && Number.isFinite(+lon) ? { latitude: +lat, longitude: +lon } : null;
  const location = sel.regionId ? { country: sel.country, region_id: sel.regionId } : coords ? { country: sel.country, ...coords } : null;
  const range = useMemo(() => {
    const end = new Date();
    end.setUTCDate(end.getUTCDate() - 1);
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - (days - 1));
    return { start_date: isoDate(start), end_date: isoDate(end) };
  }, [days]);

  const current = useQuery({
    queryKey: ["weather-current", location],
    queryFn: () => getCurrentWeather(location!),
    enabled: location !== null,
    staleTime: 10 * 60_000,
  });
  const history = useQuery({
    queryKey: ["weather-history", location, range],
    queryFn: () => getWeatherHistory({ ...location!, ...range }),
    enabled: location !== null,
    staleTime: 60 * 60_000,
  });

  const c = current.data;
  return (
    <>
      <PageHeader title="Environmental intelligence"
        description="Current and recent weather as context for malaria surveillance. Weather does not establish malaria prevalence, risk or an outbreak." />
      <SelectionBar />
      {!sel.regionId && (
        <div className="mb-4 flex flex-col gap-2 rounded-lg border border-line bg-white p-3 sm:flex-row sm:items-end">
          <p className="text-xs text-ink-2 sm:mr-2 sm:max-w-xs">Select a region above, or enter coordinates:</p>
          <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">Latitude
            <input inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="e.g. -0.09"
              className="w-32 rounded-md border border-line px-2.5 py-1.5 text-sm" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-ink-2">Longitude
            <input inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} placeholder="e.g. 34.77"
              className="w-32 rounded-md border border-line px-2.5 py-1.5 text-sm" />
          </label>
        </div>
      )}

      {location === null ? (
        <EmptyState title="Choose a location" message="Weather is retrieved for a point: select a region or enter latitude and longitude." />
      ) : (
        <>
          <Card title="Current conditions" subtitle={c ? `Observed ${dateTime(c.observed_at)} · ${c.provider} · retrieved ${dateTime(c.retrieved_at)}` : undefined}>
            {current.isLoading ? <Loading /> : current.isError ? <ErrorState error={current.error} onRetry={() => current.refetch()} /> : c && (
              <>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <Kpi label="Temperature" value={c.temperature_c === null ? null : decimal(c.temperature_c, 1, " °C")} />
                  <Kpi label="Relative humidity" value={c.relative_humidity_percent === null ? null : decimal(c.relative_humidity_percent, 0, "%")} />
                  <Kpi label="Precipitation" value={c.precipitation_mm === null ? null : decimal(c.precipitation_mm, 1, " mm")} />
                  <Kpi label="Wind speed" value={c.wind_speed_kmh === null ? null : decimal(c.wind_speed_kmh, 0, " km/h")} />
                </div>
                <ul className="mt-3 list-disc space-y-0.5 pl-5 text-xs text-ink-3">{c.notes.map((n) => <li key={n}>{n}</li>)}</ul>
              </>
            )}
          </Card>

          <Card className="mt-4" title="Recent history" subtitle={history.data ? `${history.data.data_type} · ${history.data.provider}` : undefined}
            action={
              <select aria-label="History period" value={days} onChange={(e) => setDays(Number(e.target.value))}
                className="rounded-md border border-line bg-white px-2 py-1 text-xs">
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last 12 months</option>
              </select>}>
            {history.isLoading ? <Loading /> : history.isError ? <ErrorState error={history.error} onRetry={() => history.refetch()} />
              : !history.data?.records.length ? <EmptyState message="No historical records were returned for this period." /> : (
              // Two charts on a shared date axis instead of one dual-axis chart.
              <div className="space-y-4">
                <div className="h-48 w-full" role="img" aria-label="Daily rainfall in millimetres">
                  <p className="mb-1 text-xs font-medium text-ink-2">Daily rainfall (mm)</p>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={history.data.records} margin={{ left: 4, right: 8 }} syncId="weather">
                      <CartesianGrid vertical={false} stroke="#e3e6ea" />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#4a5563" }} minTickGap={24} />
                      <YAxis tick={{ fontSize: 10, fill: "#4a5563" }} width={40} />
                      <Tooltip formatter={(v) => [v === null ? "Not available" : `${v} mm`, "Rainfall"]} />
                      <Bar dataKey="precipitation_mm" name="Rainfall (mm)" fill="#6da7ec" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-48 w-full" role="img" aria-label="Daily mean, minimum and maximum temperature">
                  <p className="mb-1 text-xs font-medium text-ink-2">Daily temperature (°C)</p>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={history.data.records} margin={{ left: 4, right: 8 }} syncId="weather">
                      <CartesianGrid vertical={false} stroke="#e3e6ea" />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#4a5563" }} minTickGap={24} />
                      <YAxis tick={{ fontSize: 10, fill: "#4a5563" }} width={40} domain={["auto", "auto"]} />
                      <Tooltip formatter={(v, n) => [v === null ? "Not available" : `${v} °C`, n]} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Line dataKey="temperature_mean_c" name="Mean" stroke="#b45309" dot={false} strokeWidth={2} />
                      <Line dataKey="temperature_min_c" name="Minimum" stroke="#6b7480" dot={false} strokeDasharray="3 3" />
                      <Line dataKey="temperature_max_c" name="Maximum" stroke="#1f4d78" dot={false} strokeDasharray="3 3" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </Card>
          <div className="mt-4"><Notice>Weather is contextual information only. It is not a malaria risk score and does not confirm an outbreak.</Notice></div>
        </>
      )}
    </>
  );
}

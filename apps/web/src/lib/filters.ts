import type { ReadonlyURLSearchParams } from "next/navigation";

import type { RangeFilters } from "./api";
import { rangeForPreset, type RangePreset } from "./date-presets";

export interface DashboardFilters extends RangeFilters {
  preset: RangePreset;
}

export const DEFAULT_TZ = "Europe/Warsaw";
export const DEFAULT_PRESET: RangePreset = "7d";

export function parseFilters(params: URLSearchParams | ReadonlyURLSearchParams | Record<string, string | undefined>): DashboardFilters {
  const get = (k: string): string | null => {
    if (params instanceof URLSearchParams) return params.get(k);
    const maybeURLSearch = params as unknown as { get?: (key: string) => string | null };
    if (typeof maybeURLSearch.get === "function") return maybeURLSearch.get(k);
    return (params as Record<string, string | undefined>)[k] ?? null;
  };
  const tz = get("tz") || DEFAULT_TZ;
  const preset = (get("preset") as RangePreset | null) || DEFAULT_PRESET;
  let from = get("from");
  let to = get("to");
  if (!from || !to) {
    const r = rangeForPreset(preset, tz);
    from = from || r.from;
    to = to || r.to;
  }
  return {
    from,
    to,
    tz,
    brand: get("brand") || "all",
    status: get("status") || "all",
    preset,
  };
}

export function filtersToQueryString(f: Partial<DashboardFilters>): string {
  const p = new URLSearchParams();
  if (f.from) p.set("from", f.from);
  if (f.to) p.set("to", f.to);
  if (f.tz && f.tz !== DEFAULT_TZ) p.set("tz", f.tz);
  if (f.brand && f.brand !== "all") p.set("brand", f.brand);
  if (f.status && f.status !== "all") p.set("status", f.status);
  if (f.preset && f.preset !== DEFAULT_PRESET) p.set("preset", f.preset);
  return p.toString();
}

export function brandLabel(b: string): string {
  if (b === "salespros") return "Salespros";
  if (b === "gawronify") return "GAWRONIFY";
  if (b === "other") return "Inne";
  return "Wszystkie";
}

export function brandColor(b: string): string {
  // Tailwind classes
  if (b === "salespros") return "bg-blue-500/15 text-blue-300 border-blue-500/30";
  if (b === "gawronify") return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  return "bg-zinc-500/15 text-zinc-300 border-zinc-500/30";
}

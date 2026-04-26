"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useTransition } from "react";
import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import { PRESET_LABELS, type RangePreset, rangeForPreset } from "@/lib/date-presets";
import { DEFAULT_TZ, parseFilters } from "@/lib/filters";

const TZ_OPTIONS = [
  { value: "Europe/Warsaw", label: "Polska (Europe/Warsaw)" },
  { value: "Asia/Makassar", label: "Bali (Asia/Makassar)" },
  { value: "UTC", label: "UTC" },
];

const BRAND_OPTIONS = [
  { value: "all", label: "Wszystkie marki" },
  { value: "salespros", label: "Salespros" },
  { value: "gawronify", label: "GAWRONIFY" },
  { value: "other", label: "Inne" },
];

export function FilterBar({ lastUpdated }: { lastUpdated?: string | null }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const filters = parseFilters(search);

  const updateParams = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(search.toString());
    for (const [k, v] of Object.entries(changes)) {
      if (v === undefined || v === "" || v === null) next.delete(k);
      else next.set(k, v);
    }
    startTransition(() => router.push(`${pathname}?${next.toString()}`));
  };

  const onPreset = (preset: RangePreset) => {
    if (preset === "custom") {
      updateParams({ preset });
      return;
    }
    const r = rangeForPreset(preset, filters.tz || DEFAULT_TZ);
    updateParams({ preset, from: r.from, to: r.to });
  };

  const onTz = (tz: string) => {
    const r = rangeForPreset((filters.preset as RangePreset) || "7d", tz);
    updateParams({ tz: tz === DEFAULT_TZ ? undefined : tz, from: r.from, to: r.to });
  };

  const onBrand = (brand: string) => updateParams({ brand: brand === "all" ? undefined : brand });

  const onRefresh = async () => {
    await api.refresh();
    router.refresh();
  };

  return (
    <div className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-10">
      <div className="flex items-center gap-3 px-6 py-3 flex-wrap">
        <Select value={filters.preset} onValueChange={(v) => onPreset(v as RangePreset)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(PRESET_LABELS).map(([k, label]) => (
              <SelectItem key={k} value={k}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="text-sm text-muted-foreground tabular-nums">
          {filters.from} → {filters.to}
        </div>

        <Separator orientation="vertical" className="h-6" />

        <Select value={filters.tz || DEFAULT_TZ} onValueChange={onTz}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TZ_OPTIONS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filters.brand || "all"} onValueChange={onBrand}>
          <SelectTrigger className="w-[170px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {BRAND_OPTIONS.map((b) => (
              <SelectItem key={b.value} value={b.value}>
                {b.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground tabular-nums">
              Last updated: {new Date(lastUpdated).toLocaleTimeString("pl-PL")}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={isPending}>
            <RotateCw className={isPending ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>
      </div>
    </div>
  );
}

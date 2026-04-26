import { Suspense } from "react";

import { FilterBar } from "@/components/filter-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fInt, fPln, fRatio } from "@/lib/format";
import { parseFilters } from "@/lib/filters";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<Record<string, string | undefined>>;
}

async function FunnelContent({ filters }: { filters: ReturnType<typeof parseFilters> }) {
  const data = await api.funnel(filters).catch((e: Error) => ({ error: e.message } as const));
  if ("error" in data) {
    return <div className="text-rose-400 text-sm">Błąd API: {data.error}</div>;
  }
  const maxCount = Math.max(1, ...data.stages.map((s) => s.count));

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pipeline: {data.pipeline_name}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {data.stages.map((s, i) => {
              const drop = data.dropoff[i - 1];
              const widthPct = (s.count / maxCount) * 100;
              return (
                <div key={s.stage_name}>
                  {drop && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground py-1 pl-4">
                      <div className="w-2 h-px bg-border" />
                      drop-off {fRatio(drop.rate)}
                    </div>
                  )}
                  <div className="relative">
                    <div
                      className="bg-blue-500/20 border border-blue-500/40 rounded h-12 flex items-center"
                      style={{ width: `${Math.max(widthPct, 8)}%` }}
                    >
                      <div className="px-3 text-sm font-medium tabular-nums truncate">{s.stage_name}</div>
                    </div>
                    <div className="absolute right-0 top-0 h-12 flex items-center gap-3 pr-3 text-sm tabular-nums">
                      <span className="font-bold">{fInt(s.count)}</span>
                      {s.value_pln > 0 && <span className="text-emerald-400">{fPln(s.value_pln)}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Note</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <div>
            Stages bookingu: <span className="text-foreground">Umówiona rozmowa</span> →{" "}
            <span className="text-foreground">Followup po rozmowie</span> → <span className="text-foreground">Nowy klient</span> → <span className="text-foreground">Opłacony START</span>.
          </div>
          <div>Filtr po `lastStageChangeAt` w wybranym zakresie dat.</div>
        </CardContent>
      </Card>
    </div>
  );
}

export default async function Page({ searchParams }: Props) {
  const filters = parseFilters(await searchParams);
  return (
    <>
      <Suspense fallback={<FilterBar />}>
        <FilterBar />
      </Suspense>
      <div className="px-6 py-6">
        <h1 className="text-2xl font-bold tracking-tight mb-6">Pipeline funnel</h1>
        <Suspense fallback={<div className="text-sm text-muted-foreground">Ładowanie…</div>}>
          <FunnelContent filters={filters} />
        </Suspense>
      </div>
    </>
  );
}

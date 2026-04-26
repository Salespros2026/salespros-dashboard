import { Suspense } from "react";

import { CreativesTable } from "./creatives-table";
import { FilterBar } from "@/components/filter-bar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fPln } from "@/lib/format";
import { parseFilters } from "@/lib/filters";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<Record<string, string | undefined>>;
}

async function CreativesContent({ filters }: { filters: ReturnType<typeof parseFilters> }) {
  const data = await api.creatives(filters).catch((e: Error) => ({ error: e.message } as const));
  if ("error" in data) {
    return <div className="text-rose-400 text-sm">Błąd API: {data.error}</div>;
  }
  const winners = data.creatives.filter((c) => c.winner_badge).length;
  const losers = data.creatives.filter((c) => c.loser_badge).length;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Kontekst</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <div>Średni real CPL: <span className="text-foreground tabular-nums">{fPln(data.avg_real_cpl)}</span></div>
          <div>Winner badges (real CPL &lt; 80% średniej, spend ≥30 PLN): <span className="text-emerald-400">{winners}</span></div>
          <div>Loser badges (real CPL &gt; 150% średniej, spend ≥50 PLN): <span className="text-rose-400">{losers}</span></div>
        </CardContent>
      </Card>
      <CreativesTable rows={data.creatives} filters={filters} />
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
        <h1 className="text-2xl font-bold tracking-tight mb-1">Kreacje</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Sortuj po real CPL ASC żeby zobaczyć top performerów. Klik na rząd → drill-down z trendem 14d i listą leadów GHL.
        </p>
        <Suspense fallback={<div className="text-sm text-muted-foreground">Ładowanie…</div>}>
          <CreativesContent filters={filters} />
        </Suspense>
      </div>
    </>
  );
}

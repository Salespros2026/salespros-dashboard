import { Suspense } from "react";

import { FilterBar } from "@/components/filter-bar";
import { KpiCard } from "@/components/kpi-card";
import { TrendChart } from "@/components/trend-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fInt, fPln } from "@/lib/format";
import { parseFilters } from "@/lib/filters";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<Record<string, string | undefined>>;
}

async function OverviewContent({ filters }: { filters: ReturnType<typeof parseFilters> }) {
  const data = await api.overview(filters).catch((e: Error) => {
    return { error: e.message } as const;
  });

  if ("error" in data) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-rose-400 text-sm">Błąd API: {data.error}</div>
          <div className="text-xs text-muted-foreground mt-2">
            Sprawdź czy backend jest uruchomiony: <code className="bg-muted px-1 rounded">uvicorn app.main:app --port 8000</code>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Wydatek"
          value={fPln(data.spend)}
          subtitle={`${data.from_} → ${data.to}`}
        />
        <KpiCard
          label="Real leady (GHL)"
          value={fInt(data.real_leads)}
          subtitle={`Meta raportuje: ${fInt(data.meta_leads)} (zawyża)`}
          tooltip="Real leady = kontakty w GHL z mailem lub telefonem (filter is_real_lead). Meta zlicza też view-throughy i pixel duplikaty."
        />
        <KpiCard
          label="Real CPL"
          value={fPln(data.real_cpl)}
          subtitle={`Meta CPL: ${fPln(data.meta_cpl)}`}
          tooltip="Real CPL = spend / real leady GHL. Meta CPL ≈ 3× zawyżony przez Custom Conversion fires."
          highlight={
            data.real_cpl == null ? undefined : data.real_cpl > 20 ? "danger" : data.real_cpl > 15 ? "warning" : "success"
          }
        />
        <KpiCard
          label="Bookingi"
          value={fInt(data.bookings)}
          subtitle={`Real CPB: ${fPln(data.real_cpb)} | Sales: ${data.sales}`}
          tooltip='Booking = opportunity w stage "Umówiona rozmowa" w pipeline SalesPROs closing.'
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            Trend dzienny
            <span className="text-xs font-normal text-muted-foreground">
              IG-sync ghosts ({fInt(data.ig_sync_ghosts)}) odfiltrowane · źródło: {data.data_source}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <TrendChart data={data.daily_trend} />
        </CardContent>
      </Card>
    </div>
  );
}

async function FilterBarFromOverview({ filters }: { filters: ReturnType<typeof parseFilters> }) {
  const data = await api.overview(filters).catch(() => null);
  return <FilterBar lastUpdated={data?.last_updated_iso ?? null} />;
}

export default async function Page({ searchParams }: Props) {
  const params = await searchParams;
  const filters = parseFilters(params);
  return (
    <>
      <Suspense fallback={<FilterBar />}>
        <FilterBarFromOverview filters={filters} />
      </Suspense>
      <div className="px-6 py-6">
        <h1 className="text-2xl font-bold tracking-tight mb-6">Overview</h1>
        <Suspense fallback={<div className="text-sm text-muted-foreground">Ładowanie…</div>}>
          <OverviewContent filters={filters} />
        </Suspense>
      </div>
    </>
  );
}

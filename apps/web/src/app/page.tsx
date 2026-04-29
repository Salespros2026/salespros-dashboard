import Link from "next/link";
import { Suspense } from "react";
import { AlertTriangle } from "lucide-react";

import { FilterBar } from "@/components/filter-bar";
import { KpiCard } from "@/components/kpi-card";
import { TrendChart } from "@/components/trend-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fInt, fPln } from "@/lib/format";
import { parseFilters } from "@/lib/filters";

export const revalidate = 60;

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

  const split = data.split;
  const totalSplitSpend = split
    ? split.spend_acquisition + split.spend_retarget + split.spend_unknown
    : 0;
  const acqPct = split && totalSplitSpend > 0 ? (split.spend_acquisition / totalSplitSpend) * 100 : 0;
  const rtgPct = split && totalSplitSpend > 0 ? (split.spend_retarget / totalSplitSpend) * 100 : 0;

  return (
    <div className="space-y-6">
      {split && split.untagged_count > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardContent className="py-3 flex items-center gap-3">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <div className="text-sm flex-1">
              <span className="font-medium text-amber-200">{split.untagged_count}</span>{" "}
              <span className="text-muted-foreground">
                {split.untagged_count === 1 ? "kampania wymaga" : "kampanii wymaga"} klasyfikacji jako acquisition lub retarget. Bez tego CPL Total miksuje koszt nowych leadów z retargetingiem.
              </span>
            </div>
            <Link
              href="/admin/campaigns"
              className="text-xs font-medium text-amber-300 hover:text-amber-200 underline underline-offset-2"
            >
              Otaguj →
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="CPL Acquisition"
          value={fPln(split?.cpl_acquisition ?? null)}
          subtitle={split ? `${fPln(split.spend_acquisition)} / ${fInt(split.leads_acquisition)} leadów` : "—"}
          tooltip="Realny koszt pozyskania nowego leada (cold). Spend kampanii oznaczonych jako acquisition / suma leadów GHL z tych kampanii."
          highlight={
            split?.cpl_acquisition == null
              ? undefined
              : split.cpl_acquisition > 25
                ? "danger"
                : split.cpl_acquisition > 18
                  ? "warning"
                  : "success"
          }
        />
        <KpiCard
          label="CPL Retarget"
          value={fPln(split?.cpl_retarget ?? null)}
          subtitle={split ? `${fPln(split.spend_retarget)} / ${fInt(split.leads_retarget)} leadów` : "—"}
          tooltip='Re-engagement istniejących leadów (warm). Strategia "Hammer them". Powinien być znacznie niższy niż CPL Acquisition.'
        />
        <KpiCard
          label="CPL Total (legacy)"
          value={fPln(data.real_cpl)}
          subtitle={`${fPln(data.spend)} / ${fInt(data.real_leads)} leadów`}
          tooltip="Spend całego konta / wszystkich realnych leadów GHL — miesza acquisition z retargetingiem. Patrz CPL Acquisition żeby zobaczyć realny koszt nowego leada."
        />
        <KpiCard
          label="Bookingi"
          value={fInt(data.bookings)}
          subtitle={`Real CPB: ${fPln(data.real_cpb)} | Sales: ${data.sales}`}
          tooltip='Booking = opportunity w stage "Umówiona rozmowa" w pipeline SalesPROs closing.'
        />
      </div>

      {split && totalSplitSpend > 0 && (
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
              <span>Spend split: {acqPct.toFixed(0)}% Acquisition · {rtgPct.toFixed(0)}% Retarget{split.spend_unknown > 0 ? ` · ${(100 - acqPct - rtgPct).toFixed(0)}% Untagged` : ""}</span>
              <span className="tabular-nums">{fPln(totalSplitSpend)} łącznie</span>
            </div>
            <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="bg-emerald-500" style={{ width: `${acqPct}%` }} />
              <div className="bg-blue-500" style={{ width: `${rtgPct}%` }} />
              {split.spend_unknown > 0 && (
                <div className="bg-amber-500" style={{ width: `${100 - acqPct - rtgPct}%` }} />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="ROAS"
          value={data.roas == null ? "—" : `${data.roas.toFixed(2)}×`}
          subtitle={split ? `ACQ: ${split.roas_acquisition == null ? "—" : split.roas_acquisition.toFixed(2) + "×"} | RTG: ${split.roas_retarget == null ? "—" : split.roas_retarget.toFixed(2) + "×"}` : `Revenue: ${fPln(data.revenue)}`}
          tooltip="Return on Ad Spend = revenue z zamkniętych sprzedaży / spend. ROAS 1× = wychodzimy na zero, 3× = 3 zł revenue na każdą złotówkę reklamy."
          highlight={
            data.roas == null ? undefined : data.roas >= 3 ? "success" : data.roas >= 1.5 ? "warning" : "danger"
          }
        />
        <KpiCard
          label="CPA"
          value={fPln(data.cpa)}
          subtitle={split ? `ACQ: ${fPln(split.cpa_acquisition)} | RTG: ${fPln(split.cpa_retarget)}` : `${data.sales} sprzedaży`}
          tooltip='CPA = spend / liczba zamkniętych sprzedaży (stage "Nowy klient" + "Opłacony START"). Pokazuje koszt pozyskania klienta, nie tylko leada.'
        />
        <KpiCard
          label="Revenue"
          value={fPln(data.revenue)}
          subtitle={split ? `ACQ: ${fPln(split.revenue_acquisition)} | RTG: ${fPln(split.revenue_retarget)}` : `${data.sales} sprzedaży`}
          tooltip="Suma monetaryValue z opportunities zamkniętych jako sprzedaż w wybranym zakresie dat."
        />
        <KpiCard
          label="Sprzedaże"
          value={fInt(data.sales)}
          subtitle={split ? `ACQ: ${fInt(split.sales_acquisition)} | RTG: ${fInt(split.sales_retarget)}` : "—"}
          tooltip='Liczba zamkniętych sprzedaży (opportunity w "Nowy klient" lub "Opłacony START").'
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

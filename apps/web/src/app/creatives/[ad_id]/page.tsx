import { Suspense } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, ImageOff } from "lucide-react";

import { FilterBar } from "@/components/filter-bar";
import { BrandBadge } from "@/components/brand-badge";
import { TrendChart } from "@/components/trend-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { fDateTime } from "@/lib/format";
import { filtersToQueryString, parseFilters } from "@/lib/filters";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ ad_id: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}

async function DetailContent({ adId, filters }: { adId: string; filters: ReturnType<typeof parseFilters> }) {
  const data = await api.creativeDetail(adId, filters).catch((e: Error) => ({ error: e.message } as const));
  if ("error" in data) {
    return <div className="text-rose-400 text-sm">Błąd: {data.error}</div>;
  }
  const c = data.creative as Record<string, string | undefined>;
  const thumb = c.thumbnail_url || c.image_url;
  const qs = filtersToQueryString(filters);

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4 flex-wrap">
        <Button variant="ghost" size="sm" asChild>
          <Link href={qs ? `/creatives?${qs}` : "/creatives"}>
            <ArrowLeft />
            Wróć
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <BrandBadge brand={data.brand} />
            <span className="text-sm text-muted-foreground truncate">{data.campaign_name}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{data.ad_name}</h1>
          <div className="text-xs text-muted-foreground mt-1 font-mono">ad_id: {data.ad_id}</div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Kreacja</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {thumb ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={thumb} alt="" className="w-full rounded object-cover bg-muted aspect-square" />
            ) : (
              <div className="w-full aspect-square rounded bg-muted flex items-center justify-center text-muted-foreground/50">
                <ImageOff className="h-8 w-8" />
              </div>
            )}
            {c.title && <div className="text-sm font-medium">{c.title}</div>}
            {c.body && <div className="text-xs text-muted-foreground line-clamp-6">{c.body}</div>}
            {c.video_id && (
              <div className="text-xs">
                <span className="text-muted-foreground">video_id:</span>{" "}
                <a
                  href={`https://www.facebook.com/${c.video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  {c.video_id} <ExternalLink className="h-3 w-3 inline" />
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Trend dzienny</CardTitle>
          </CardHeader>
          <CardContent>
            <TrendChart data={data.trend} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Leady GHL z tej kreacji ({data.leads.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.leads.length === 0 ? (
            <div className="text-sm text-muted-foreground py-4">
              W tym zakresie czasu brak realnych leadów (z mailem/telefonem) zaatrybuowanych do tego ada.
            </div>
          ) : (
            <div className="space-y-2">
              {data.leads.map((lead) => (
                <a
                  key={lead.contact_id}
                  href={lead.ghl_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-4 px-3 py-2 rounded border border-border hover:bg-accent/40 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{lead.name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {lead.email || "(brak email)"} · {lead.phone || "(brak tel)"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {lead.sold && <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40">Sale</Badge>}
                    {lead.booked && <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/40">Booked</Badge>}
                    <span className="text-xs text-muted-foreground tabular-nums">{fDateTime(lead.date_added)}</span>
                    <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </a>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default async function Page({ params, searchParams }: Props) {
  const { ad_id } = await params;
  const filters = parseFilters(await searchParams);
  return (
    <>
      <Suspense fallback={<FilterBar />}>
        <FilterBar />
      </Suspense>
      <div className="px-6 py-6">
        <Suspense fallback={<div className="text-sm text-muted-foreground">Ładowanie…</div>}>
          <DetailContent adId={ad_id} filters={filters} />
        </Suspense>
      </div>
    </>
  );
}

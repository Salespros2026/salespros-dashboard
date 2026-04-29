import { Suspense } from "react";

import { CampaignsTable } from "./campaigns-table";
import { FilterBar } from "@/components/filter-bar";
import { api } from "@/lib/api";
import { parseFilters } from "@/lib/filters";

export const revalidate = 60;

interface Props {
  searchParams: Promise<Record<string, string | undefined>>;
}

async function CampaignsContent({ filters }: { filters: ReturnType<typeof parseFilters> }) {
  const data = await api.campaigns(filters).catch((e: Error) => ({ error: e.message } as const));
  if ("error" in data) {
    return <div className="text-rose-400 text-sm">Błąd API: {data.error}</div>;
  }
  return <CampaignsTable rows={data.campaigns} />;
}

export default async function Page({ searchParams }: Props) {
  const filters = parseFilters(await searchParams);
  return (
    <>
      <Suspense fallback={<FilterBar />}>
        <FilterBar />
      </Suspense>
      <div className="px-6 py-6">
        <h1 className="text-2xl font-bold tracking-tight mb-6">Kampanie</h1>
        <Suspense fallback={<div className="text-sm text-muted-foreground">Ładowanie…</div>}>
          <CampaignsContent filters={filters} />
        </Suspense>
      </div>
    </>
  );
}

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { FilterBar } from "@/components/filter-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { CampaignsAdminTable } from "./campaigns-admin-table";

export const revalidate = 60;

async function AdminContent() {
  const data = await api.adminCampaigns().catch((e: Error) => ({ error: e.message } as const));

  if ("error" in data) {
    return (
      <Card>
        <CardContent className="py-8 text-rose-400 text-sm">Błąd API: {data.error}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        Otaguj kampanie jako <span className="text-emerald-300 font-medium">acquisition</span> (cold leady, nowe pozyskanie) lub
        <span className="text-blue-300 font-medium"> retarget</span> (warm — istniejący kontakty z bazy, np. strategia &quot;Hammer them&quot;). Tagi zmieniają jak liczone są CPL Acquisition vs CPL Retarget na overview.
      </div>
      <CampaignsAdminTable rows={data.campaigns} initialUntagged={data.untagged_count} />
    </div>
  );
}

export default function Page() {
  return (
    <>
      <FilterBar />
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
              Overview
            </Link>
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">Klasyfikacja kampanii</h1>
        </div>
        <AdminContent />
      </div>
    </>
  );
}

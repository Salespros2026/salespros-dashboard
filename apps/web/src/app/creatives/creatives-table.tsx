"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useRouter } from "next/navigation";
import { Trophy, AlertTriangle, ImageOff } from "lucide-react";

import { BrandBadge } from "@/components/brand-badge";
import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { filtersToQueryString, type DashboardFilters } from "@/lib/filters";
import { fInt, fPct, fPln, fRatio } from "@/lib/format";
import type { CreativeRow } from "@/lib/types";

const columns: ColumnDef<CreativeRow>[] = [
  {
    id: "thumbnail",
    header: "",
    enableSorting: false,
    cell: ({ row }) => {
      const url = row.original.thumbnail_url;
      if (!url) {
        return (
          <div className="w-12 h-12 rounded bg-muted flex items-center justify-center text-muted-foreground/50">
            <ImageOff className="h-4 w-4" />
          </div>
        );
      }
      return (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt=""
          className="w-12 h-12 rounded object-cover bg-muted"
          loading="lazy"
        />
      );
    },
  },
  {
    accessorKey: "ad_name",
    header: "Ad",
    cell: ({ row }) => (
      <div className="flex flex-col gap-1 min-w-0 max-w-[280px]">
        <div className="flex items-center gap-2">
          <BrandBadge brand={row.original.brand} />
          {row.original.winner_badge && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 gap-1">
                  <Trophy className="h-3 w-3" /> Winner
                </Badge>
              </TooltipTrigger>
              <TooltipContent>Real CPL &lt; 80% średniej.</TooltipContent>
            </Tooltip>
          )}
          {row.original.loser_badge && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-rose-500/20 text-rose-300 border-rose-500/40 gap-1">
                  <AlertTriangle className="h-3 w-3" /> Pause?
                </Badge>
              </TooltipTrigger>
              <TooltipContent>Real CPL &gt; 150% średniej, spend ≥50 PLN — kandydat do pauzy.</TooltipContent>
            </Tooltip>
          )}
        </div>
        <span className="truncate text-sm" title={row.original.ad_name}>{row.original.ad_name}</span>
        <span className="truncate text-xs text-muted-foreground" title={row.original.campaign_name}>
          {row.original.campaign_name}
        </span>
      </div>
    ),
  },
  { accessorKey: "spend", header: "Spend", cell: ({ getValue }) => fPln(getValue<number>()) },
  { accessorKey: "ghl_leads", header: "Real leady", cell: ({ getValue }) => fInt(getValue<number>()) },
  { accessorKey: "meta_leads", header: "Meta leady", cell: ({ getValue }) => <span className="text-muted-foreground">{fInt(getValue<number>())}</span> },
  {
    accessorKey: "real_cpl",
    header: "Real CPL",
    cell: ({ getValue }) => {
      const v = getValue<number | null>();
      const color = v == null ? "" : v > 20 ? "text-rose-400" : v > 15 ? "text-amber-400" : "text-emerald-400";
      return <span className={`font-medium ${color}`}>{fPln(v)}</span>;
    },
  },
  { accessorKey: "bookings", header: "Bookingi", cell: ({ getValue }) => fInt(getValue<number>()) },
  { accessorKey: "ctr", header: "CTR", cell: ({ getValue }) => fPct(getValue<number>()) },
  {
    accessorKey: "frequency",
    header: "Freq.",
    cell: ({ getValue }) => {
      const v = getValue<number>();
      const color = v > 3.5 ? "text-rose-400" : v > 2.5 ? "text-amber-400" : "";
      return <span className={color}>{v ? v.toFixed(2) : "—"}</span>;
    },
  },
  {
    accessorKey: "hook_rate",
    header: "Hook",
    cell: ({ getValue }) => fRatio(getValue<number | null>()),
  },
];

export function CreativesTable({ rows, filters }: { rows: CreativeRow[]; filters: DashboardFilters }) {
  const router = useRouter();
  const qs = filtersToQueryString(filters);
  return (
    <DataTable
      columns={columns}
      data={rows}
      initialSort={[{ id: "spend", desc: true }]}
      onRowClick={(r) => router.push(`/creatives/${encodeURIComponent(r.ad_id)}${qs ? `?${qs}` : ""}`)}
      rowClassName={(r) =>
        r.winner_badge ? "border-l-2 border-l-emerald-500/60" : r.loser_badge ? "border-l-2 border-l-rose-500/60" : undefined
      }
    />
  );
}

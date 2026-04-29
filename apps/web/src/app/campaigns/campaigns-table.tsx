"use client";

import { ColumnDef } from "@tanstack/react-table";

import { BrandBadge } from "@/components/brand-badge";
import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { fInt, fPct, fPln } from "@/lib/format";
import type { CampaignRow } from "@/lib/types";

const columns: ColumnDef<CampaignRow>[] = [
  {
    accessorKey: "name",
    header: "Kampania",
    cell: ({ row }) => (
      <div className="flex items-center gap-2 min-w-0">
        <BrandBadge brand={row.original.brand} />
        <span className="truncate max-w-[280px]" title={row.original.name}>
          {row.original.name}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const s = row.original.status;
      const isActive = s === "ACTIVE";
      return (
        <Badge variant={isActive ? "default" : "secondary"} className={isActive ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" : ""}>
          {s}
        </Badge>
      );
    },
  },
  {
    accessorKey: "campaign_type",
    header: "Typ",
    cell: ({ row }) => {
      const t = row.original.campaign_type;
      const isManual = row.original.is_manual_type;
      const cls =
        t === "acquisition"
          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
          : t === "retarget"
            ? "bg-blue-500/15 text-blue-300 border-blue-500/30"
            : "bg-amber-500/15 text-amber-300 border-amber-500/30";
      const label = t === "acquisition" ? "ACQ" : t === "retarget" ? "RTG" : "?";
      return (
        <Badge variant="outline" className={cls} title={isManual ? "Tag ustawiony manualnie" : "Tag z auto-rules — kliknij /admin/campaigns żeby override"}>
          {label}
          {!isManual && t !== "unknown" && <span className="ml-1 opacity-60">auto</span>}
        </Badge>
      );
    },
  },
  {
    accessorKey: "spend",
    header: "Spend",
    cell: ({ getValue }) => fPln(getValue<number>()),
  },
  {
    accessorKey: "ghl_leads",
    header: "Leady (real)",
    cell: ({ getValue }) => fInt(getValue<number>()),
  },
  {
    accessorKey: "meta_leads",
    header: "Meta leady",
    cell: ({ getValue }) => <span className="text-muted-foreground">{fInt(getValue<number>())}</span>,
  },
  {
    accessorKey: "real_cpl",
    header: "Real CPL",
    cell: ({ getValue }) => {
      const v = getValue<number | null>();
      const color = v == null ? "" : v > 20 ? "text-rose-400" : v > 15 ? "text-amber-400" : "text-emerald-400";
      return <span className={color}>{fPln(v)}</span>;
    },
  },
  {
    accessorKey: "bookings",
    header: "Bookingi",
    cell: ({ getValue }) => fInt(getValue<number>()),
  },
  {
    accessorKey: "sales",
    header: "Sales",
    cell: ({ getValue }) => fInt(getValue<number>()),
  },
  {
    accessorKey: "revenue",
    header: "Revenue",
    cell: ({ getValue }) => {
      const v = getValue<number>();
      return <span className={v > 0 ? "text-emerald-300" : "text-muted-foreground"}>{fPln(v || null)}</span>;
    },
  },
  {
    accessorKey: "cpa",
    header: "CPA",
    cell: ({ getValue }) => fPln(getValue<number | null>()),
  },
  {
    accessorKey: "roas",
    header: "ROAS",
    cell: ({ getValue }) => {
      const v = getValue<number | null>();
      if (v == null) return <span className="text-muted-foreground">—</span>;
      const color = v >= 3 ? "text-emerald-400" : v >= 1.5 ? "text-amber-400" : "text-rose-400";
      return <span className={color}>{v.toFixed(2)}×</span>;
    },
  },
  {
    accessorKey: "ctr",
    header: "CTR",
    cell: ({ getValue }) => fPct(getValue<number>()),
  },
  {
    accessorKey: "frequency",
    header: "Freq.",
    cell: ({ getValue }) => {
      const v = getValue<number>();
      const color = v > 3.5 ? "text-rose-400" : v > 2.5 ? "text-amber-400" : "";
      return <span className={color}>{v ? v.toFixed(2) : "—"}</span>;
    },
  },
];

export function CampaignsTable({ rows }: { rows: CampaignRow[] }) {
  return <DataTable columns={columns} data={rows} initialSort={[{ id: "spend", desc: true }]} />;
}

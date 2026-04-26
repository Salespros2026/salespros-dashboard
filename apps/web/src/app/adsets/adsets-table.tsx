"use client";

import { ColumnDef } from "@tanstack/react-table";

import { BrandBadge } from "@/components/brand-badge";
import { DataTable } from "@/components/data-table";
import { fInt, fPct, fPln } from "@/lib/format";
import type { AdsetRow } from "@/lib/types";

const columns: ColumnDef<AdsetRow>[] = [
  {
    accessorKey: "name",
    header: "Adset",
    cell: ({ row }) => (
      <div className="flex items-center gap-2 min-w-0">
        <BrandBadge brand={row.original.brand} />
        <span className="truncate max-w-[260px]" title={row.original.name}>
          {row.original.name}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "parent_campaign_name",
    header: "Kampania",
    cell: ({ getValue }) => (
      <span className="text-muted-foreground truncate max-w-[200px] block" title={getValue<string>()}>
        {getValue<string>()}
      </span>
    ),
  },
  { accessorKey: "optimization_goal", header: "Cel", cell: ({ getValue }) => getValue<string>() ?? "—" },
  { accessorKey: "spend", header: "Spend", cell: ({ getValue }) => fPln(getValue<number>()) },
  { accessorKey: "ghl_leads", header: "Leady (real)", cell: ({ getValue }) => fInt(getValue<number>()) },
  { accessorKey: "meta_leads", header: "Meta leady", cell: ({ getValue }) => <span className="text-muted-foreground">{fInt(getValue<number>())}</span> },
  {
    accessorKey: "real_cpl",
    header: "Real CPL",
    cell: ({ getValue }) => {
      const v = getValue<number | null>();
      const color = v == null ? "" : v > 20 ? "text-rose-400" : v > 15 ? "text-amber-400" : "text-emerald-400";
      return <span className={color}>{fPln(v)}</span>;
    },
  },
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
];

export function AdsetsTable({ rows }: { rows: AdsetRow[] }) {
  return <DataTable columns={columns} data={rows} initialSort={[{ id: "spend", desc: true }]} />;
}

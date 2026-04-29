"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fPln } from "@/lib/format";
import type { AdminCampaignRow, CampaignType } from "@/lib/types";

const TYPE_LABEL: Record<CampaignType, string> = {
  acquisition: "Acquisition",
  retarget: "Retarget",
  unknown: "Untagged",
};

const TYPE_BADGE: Record<CampaignType, string> = {
  acquisition: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  retarget: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  unknown: "bg-amber-500/15 text-amber-300 border-amber-500/30",
};

interface Props {
  rows: AdminCampaignRow[];
  initialUntagged: number;
}

export function CampaignsAdminTable({ rows, initialUntagged }: Props) {
  const router = useRouter();
  const [optimistic, setOptimistic] = useState<Record<string, { type: CampaignType; isManual: boolean }>>({});
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [isTransition, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const setPending = (id: string, on: boolean) => {
    setPendingIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const onChangeType = async (cid: string, newType: CampaignType) => {
    setError(null);
    setPending(cid, true);
    setOptimistic((p) => ({ ...p, [cid]: { type: newType, isManual: true } }));
    try {
      const res = await fetch(`/api/proxy/admin/campaigns/${encodeURIComponent(cid)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: newType }),
      });
      if (!res.ok) {
        throw new Error(`${res.status}: ${await res.text()}`);
      }
      startTransition(() => router.refresh());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nie udało się zapisać");
      setOptimistic((p) => {
        const next = { ...p };
        delete next[cid];
        return next;
      });
    } finally {
      setPending(cid, false);
    }
  };

  const onClearOverride = async (cid: string) => {
    setError(null);
    setPending(cid, true);
    try {
      const res = await fetch(`/api/proxy/admin/campaigns/${encodeURIComponent(cid)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        throw new Error(`${res.status}: ${await res.text()}`);
      }
      const body = (await res.json()) as { campaign_type: CampaignType; is_manual: boolean };
      setOptimistic((p) => ({
        ...p,
        [cid]: { type: body.campaign_type, isManual: body.is_manual },
      }));
      startTransition(() => router.refresh());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nie udało się usunąć override");
    } finally {
      setPending(cid, false);
    }
  };

  const liveRows = rows.map((r) => {
    const o = optimistic[r.campaign_id];
    if (!o) return r;
    return { ...r, campaign_type: o.type, is_manual: o.isManual };
  });

  const untagged = liveRows.filter((r) => r.campaign_type === "unknown").length || initialUntagged;

  return (
    <div className="space-y-4">
      {error && (
        <Card className="border-rose-500/40 bg-rose-500/5">
          <CardContent className="py-3 text-sm text-rose-200">Błąd: {error}</CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between text-sm">
        <div className="text-muted-foreground">
          {liveRows.length} kampanii · <span className="text-amber-300">{untagged}</span> nieotagowanych
        </div>
        {isTransition && <span className="text-xs text-muted-foreground">Synchronizacja…</span>}
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-4 py-2">Kampania</th>
              <th className="text-left px-4 py-2">Objective</th>
              <th className="text-right px-4 py-2">Spend 30d</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Aktualny tag</th>
              <th className="text-left px-4 py-2">Sugestia auto</th>
              <th className="text-left px-4 py-2">Akcje</th>
            </tr>
          </thead>
          <tbody>
            {liveRows.map((r) => {
              const isPending = pendingIds.has(r.campaign_id);
              return (
                <tr key={r.campaign_id} className="border-t border-border/40 hover:bg-muted/20">
                  <td className="px-4 py-2 max-w-[320px]">
                    <div className="truncate" title={r.name}>{r.name}</div>
                    <div className="text-xs text-muted-foreground tabular-nums">{r.campaign_id}</div>
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{r.objective || "—"}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{fPln(r.spend_30d)}</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className={r.status === "ACTIVE" ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" : ""}>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className={TYPE_BADGE[r.campaign_type]}>
                      {TYPE_LABEL[r.campaign_type]}
                      {r.is_manual && <span className="ml-1 opacity-60">manual</span>}
                      {!r.is_manual && r.campaign_type !== "unknown" && <span className="ml-1 opacity-60">auto</span>}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">
                    {r.suggested_type === "unknown" ? "—" : TYPE_LABEL[r.suggested_type]}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <Select
                        value={r.campaign_type === "unknown" ? "" : r.campaign_type}
                        onValueChange={(v) => onChangeType(r.campaign_id, v as CampaignType)}
                        disabled={isPending}
                      >
                        <SelectTrigger className="w-[150px] h-8 text-xs">
                          <SelectValue placeholder="Wybierz tag" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="acquisition">Acquisition</SelectItem>
                          <SelectItem value="retarget">Retarget</SelectItem>
                        </SelectContent>
                      </Select>
                      {r.is_manual && (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={isPending}
                          onClick={() => onClearOverride(r.campaign_id)}
                          className="text-xs h-8"
                        >
                          Reset
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {liveRows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  Brak kampanii w ostatnich 30 dniach.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

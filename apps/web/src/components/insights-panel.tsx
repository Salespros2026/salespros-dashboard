import Link from "next/link";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Insight, InsightsResponse } from "@/lib/types";

const SEVERITY_CONFIG: Record<string, { icon: typeof AlertCircle; color: string; border: string; label: string }> = {
  winner: { icon: CheckCircle2, color: "text-emerald-300", border: "border-emerald-500/40 bg-emerald-500/5", label: "WINNER" },
  warn: { icon: AlertTriangle, color: "text-amber-300", border: "border-amber-500/40 bg-amber-500/5", label: "WARN" },
  critical: { icon: AlertCircle, color: "text-rose-300", border: "border-rose-500/40 bg-rose-500/5", label: "CRITICAL" },
  info: { icon: Info, color: "text-blue-300", border: "border-blue-500/40 bg-blue-500/5", label: "INFO" },
};

function severityRank(s: string): number {
  return { critical: 0, warn: 1, winner: 2, info: 3 }[s] ?? 4;
}

export function InsightsPanel({ data }: { data: InsightsResponse | null }) {
  if (!data || !data.insights || data.insights.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-3 text-sm text-muted-foreground flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Brak AI Insights — codzienny brief generuje się o 8:30. Albo uruchom manualnie:{" "}
          <code className="text-xs bg-muted px-1 rounded">python scripts/ai_insights.py</code>
        </CardContent>
      </Card>
    );
  }

  const sorted = [...data.insights].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
  const generatedDate = data.generated_at ? new Date(data.generated_at) : null;

  return (
    <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-300" />
          AI Insights — sugestie na dziś
          {data.stale && (
            <Badge variant="outline" className="ml-2 text-xs text-amber-400 border-amber-500/40">
              starsze niż dziś
            </Badge>
          )}
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {generatedDate ? generatedDate.toLocaleString("pl-PL") : "?"}
            {data.model && <span className="ml-2 opacity-60">· {data.model.split("/").pop()}</span>}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {sorted.map((ins, i) => {
          const cfg = SEVERITY_CONFIG[ins.severity] || SEVERITY_CONFIG.info;
          const Icon = cfg.icon;
          return (
            <Card key={i} className={`${cfg.border} border`}>
              <CardContent className="py-3">
                <div className="flex items-start gap-3">
                  <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${cfg.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className={`text-xs ${cfg.color} border-current`}>
                        {cfg.label}
                      </Badge>
                      <span className="text-sm font-semibold">{ins.title}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{ins.why}</div>
                    <div className="text-xs mt-2 font-medium">→ {ins.action}</div>
                    {ins.ad_id && (
                      <Link
                        href={`/creatives/${encodeURIComponent(ins.ad_id)}`}
                        className="text-xs text-purple-300 hover:underline mt-1 inline-block"
                      >
                        Otwórz kreację →
                      </Link>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </CardContent>
    </Card>
  );
}

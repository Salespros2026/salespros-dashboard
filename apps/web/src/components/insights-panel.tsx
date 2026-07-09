import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Eye,
  Flame,
  ImageOff,
  Info,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fInt, fPln } from "@/lib/format";
import type { CreativeRow, FatigueAd, FatigueResponse, Insight, InsightsResponse } from "@/lib/types";

/* Panel "Co robić dziś" — łączy AI Insights (/api/insights) z twardymi werdyktami
   fatigue (/api/fatigue) i wzbogaca karty o miniaturki + metryki kreacji
   (/api/creatives). Trzy kubełki akcji: Wyłącz/Wymień → Skaluj → Obserwuj. */

type Bucket = "act" | "scale" | "watch";

interface ActionCard {
  bucket: Bucket;
  /** severity AI ("critical"…) lub werdykt fatigue ("kill"/"rotate"/"watch") */
  tag: string;
  title: string;
  why: string;
  action: string;
  ad_id: string | null;
  fatigueReasons: string[];
  campaignType: string | null;
  creative: CreativeRow | null;
}

const TAG_CONFIG: Record<string, { icon: typeof AlertCircle; color: string; border: string; label: string }> = {
  critical: { icon: AlertCircle, color: "text-rose-300", border: "border-rose-500/40 bg-rose-500/5", label: "CRITICAL" },
  kill: { icon: Flame, color: "text-rose-300", border: "border-rose-500/40 bg-rose-500/5", label: "WYPALONA" },
  rotate: { icon: Flame, color: "text-orange-300", border: "border-orange-500/40 bg-orange-500/5", label: "WYMIEŃ" },
  winner: { icon: CheckCircle2, color: "text-emerald-300", border: "border-emerald-500/40 bg-emerald-500/5", label: "WINNER" },
  warn: { icon: AlertTriangle, color: "text-amber-300", border: "border-amber-500/40 bg-amber-500/5", label: "WARN" },
  watch: { icon: Eye, color: "text-amber-300", border: "border-amber-500/40 bg-amber-500/5", label: "OBSERWUJ" },
  info: { icon: Info, color: "text-blue-300", border: "border-blue-500/40 bg-blue-500/5", label: "INFO" },
};

const BUCKETS: Record<Bucket, { title: string; dot: string }> = {
  act: { title: "Wyłącz / Wymień", dot: "bg-rose-500" },
  scale: { title: "Skaluj", dot: "bg-emerald-500" },
  watch: { title: "Obserwuj", dot: "bg-amber-500" },
};

function bucketForSeverity(s: string): Bucket {
  if (s === "critical") return "act";
  if (s === "winner") return "scale";
  return "watch"; // warn + info
}

function bucketForVerdict(v: string): Bucket {
  if (v === "kill" || v === "rotate") return "act";
  return "watch";
}

function verdictAction(v: string): string {
  if (v === "kill") return "Wyłącz kreację — twarde reguły fatigue (nie AI).";
  if (v === "rotate") return "Przygotuj zamiennik i wymień kreację w tym tygodniu.";
  return "Obserwuj — wczesne sygnały zmęczenia kreacji.";
}

function buildCards(
  insights: Insight[],
  fatigueAds: FatigueAd[],
  creativesById: Record<string, CreativeRow>,
): ActionCard[] {
  const cards: ActionCard[] = insights.map((ins) => ({
    bucket: bucketForSeverity(ins.severity),
    tag: ins.severity,
    title: ins.title,
    why: ins.why,
    action: ins.action,
    ad_id: ins.ad_id,
    fatigueReasons: [],
    campaignType: null,
    creative: ins.ad_id ? (creativesById[ins.ad_id] ?? null) : null,
  }));

  const byAdId = new Map<string, ActionCard>();
  for (const c of cards) if (c.ad_id) byAdId.set(c.ad_id, c);

  for (const fa of fatigueAds) {
    if (fa.verdict === "ok") continue;
    const existing = byAdId.get(fa.ad_id);
    if (existing) {
      // Dedupe: dopisz twarde reguły do karty AI; kill/rotate promuje do czerwonego kubełka.
      existing.fatigueReasons = fa.reasons;
      existing.campaignType = fa.campaign_type;
      if (bucketForVerdict(fa.verdict) === "act") existing.bucket = "act";
      continue;
    }
    const creative = creativesById[fa.ad_id] ?? null;
    cards.push({
      bucket: bucketForVerdict(fa.verdict),
      tag: fa.verdict,
      title: fa.ad_name || creative?.ad_name || fa.ad_id,
      why: fa.reasons.join("; "),
      action: verdictAction(fa.verdict),
      ad_id: fa.ad_id,
      fatigueReasons: [],
      campaignType: fa.campaign_type,
      creative,
    });
  }

  // Uzupełnij campaign_type z creatives (retarget badge) gdy fatigue go nie dał.
  for (const c of cards) {
    if (!c.campaignType && c.ad_id) {
      const fa = fatigueAds.find((f) => f.ad_id === c.ad_id);
      if (fa) c.campaignType = fa.campaign_type;
    }
  }

  const tagRank: Record<string, number> = { critical: 0, kill: 1, rotate: 2, winner: 3, warn: 4, watch: 5, info: 6 };
  return cards.sort((a, b) => (tagRank[a.tag] ?? 9) - (tagRank[b.tag] ?? 9));
}

function Thumb({ creative }: { creative: CreativeRow | null }) {
  const url = creative?.thumbnail_url;
  return url ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt="" className="w-16 h-16 rounded object-cover bg-muted shrink-0" loading="lazy" />
  ) : (
    <div className="w-16 h-16 rounded bg-muted flex items-center justify-center shrink-0">
      <ImageOff className="h-5 w-5 text-muted-foreground" />
    </div>
  );
}

function MetricsRow({ creative }: { creative: CreativeRow }) {
  const items: string[] = [];
  items.push(`spend ${fPln(creative.spend)}`);
  items.push(`real CPL ${creative.real_cpl == null ? "—" : fPln(creative.real_cpl)}`);
  items.push(`${fInt(creative.ghl_leads)} leadów`);
  if (creative.frequency) items.push(`freq ${creative.frequency.toFixed(1)}`);
  if (creative.health_score != null) items.push(`health ${creative.health_score}/100`);
  return (
    <div className="text-xs text-muted-foreground tabular-nums mt-1">
      {items.join(" · ")}
    </div>
  );
}

function ActionCardView({ card, qs }: { card: ActionCard; qs: string }) {
  const cfg = TAG_CONFIG[card.tag] || TAG_CONFIG.info;
  const Icon = cfg.icon;
  const hasCreative = Boolean(card.ad_id);

  const body = (
    <CardContent className="py-3">
      <div className="flex items-start gap-3">
        {hasCreative ? <Thumb creative={card.creative} /> : <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${cfg.color}`} />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <Badge variant="outline" className={`text-xs ${cfg.color} border-current`}>
              {cfg.label}
            </Badge>
            {card.campaignType === "retarget" && (
              <Badge variant="outline" className="text-xs text-blue-300 border-blue-500/40">
                retarget — oceniaj po sales, nie CPL
              </Badge>
            )}
            <span className="text-sm font-semibold">{card.title}</span>
          </div>
          {card.creative && (
            <div className="text-xs text-muted-foreground truncate">
              {card.creative.ad_name} · {card.creative.campaign_name}
            </div>
          )}
          {card.creative && <MetricsRow creative={card.creative} />}
          <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{card.why}</div>
          {card.fatigueReasons.length > 0 && (
            <div className="text-xs mt-1 text-orange-300/90">
              🔥 twarde reguły: {card.fatigueReasons.join("; ")}
            </div>
          )}
          <div className="text-xs mt-2 font-medium">→ {card.action}</div>
          {card.ad_id && (
            <span className="text-xs text-purple-300 mt-1 inline-block group-hover:underline">
              Otwórz kreację →
            </span>
          )}
        </div>
      </div>
    </CardContent>
  );

  if (card.ad_id) {
    return (
      <Link href={`/creatives/${encodeURIComponent(card.ad_id)}${qs ? `?${qs}` : ""}`} className="block group">
        <Card className={`${cfg.border} border transition-colors hover:border-purple-400/50`}>{body}</Card>
      </Link>
    );
  }
  return <Card className={`${cfg.border} border`}>{body}</Card>;
}

export function InsightsPanel({
  data,
  fatigue,
  creativesById = {},
  qs = "",
}: {
  data: InsightsResponse | null;
  fatigue?: FatigueResponse | null;
  creativesById?: Record<string, CreativeRow>;
  qs?: string;
}) {
  const insights = data?.insights ?? [];
  const fatigueAds = fatigue?.ads ?? [];
  const cards = buildCards(insights, fatigueAds, creativesById);

  if (cards.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-3 text-sm text-muted-foreground flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Brak werdyktów na dziś — codzienny brief generuje się o 8:00. Albo uruchom manualnie:{" "}
          <code className="text-xs bg-muted px-1 rounded">python scripts/ai_insights.py</code>
        </CardContent>
      </Card>
    );
  }

  const generatedDate = data?.generated_at ? new Date(data.generated_at) : null;
  const order: Bucket[] = ["act", "scale", "watch"];

  return (
    <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-purple-300" />
          Co robić dziś
          {(data?.stale || fatigue?.stale) && (
            <Badge variant="outline" className="ml-2 text-xs text-amber-400 border-amber-500/40">
              starsze niż dziś
            </Badge>
          )}
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {generatedDate ? generatedDate.toLocaleString("pl-PL") : "?"}
            {data?.model && <span className="ml-2 opacity-60">· {data.model.split("/").pop()} + reguły fatigue</span>}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {order.map((bucket) => {
          const items = cards.filter((c) => c.bucket === bucket);
          if (items.length === 0) return null;
          const b = BUCKETS[bucket];
          return (
            <div key={bucket}>
              <div className="flex items-center gap-2 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                <span className={`h-2 w-2 rounded-full ${b.dot}`} />
                {b.title} ({items.length})
              </div>
              <div className="space-y-2">
                {items.map((card, i) => (
                  <ActionCardView key={`${bucket}-${card.ad_id ?? i}`} card={card} qs={qs} />
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

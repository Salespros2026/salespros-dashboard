import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string;
  subtitle?: string;
  trend?: { delta: number; period: string } | null;
  tooltip?: string;
  highlight?: "success" | "warning" | "danger";
}

export function KpiCard({ label, value, subtitle, trend, tooltip, highlight }: KpiCardProps) {
  const trendColor =
    trend == null
      ? ""
      : trend.delta < 0
        ? "text-emerald-400"
        : trend.delta > 0
          ? "text-rose-400"
          : "text-muted-foreground";

  const valueColor =
    highlight === "success"
      ? "text-emerald-400"
      : highlight === "warning"
        ? "text-amber-400"
        : highlight === "danger"
          ? "text-rose-400"
          : "";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
          {label}
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">{tooltip}</TooltipContent>
            </Tooltip>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={cn("text-3xl font-bold tracking-tight tabular-nums", valueColor)}>{value}</div>
        {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
        {trend && (
          <div className={cn("text-xs mt-2 tabular-nums", trendColor)}>
            {trend.delta > 0 ? "▲" : trend.delta < 0 ? "▼" : "■"} {Math.abs(trend.delta).toFixed(1)}% vs {trend.period}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

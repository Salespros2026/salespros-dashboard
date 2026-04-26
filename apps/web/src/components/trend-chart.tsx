"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TrendPoint } from "@/lib/types";
import { fDate, fInt, fPln } from "@/lib/format";

interface Props {
  data: TrendPoint[];
}

export function TrendChart({ data }: Props) {
  if (!data?.length) {
    return (
      <div className="text-sm text-muted-foreground py-12 text-center">
        Brak danych w wybranym zakresie.
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis
          dataKey="date"
          tickFormatter={fDate}
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
          stroke="rgba(255,255,255,0.2)"
        />
        <YAxis
          yAxisId="left"
          tickFormatter={(v) => `${v} zł`}
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
          stroke="rgba(255,255,255,0.2)"
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickFormatter={fInt}
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
          stroke="rgba(255,255,255,0.2)"
        />
        <Tooltip
          contentStyle={{
            background: "oklch(0.205 0 0)",
            border: "1px solid oklch(1 0 0 / 10%)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelFormatter={(label) => fDate(String(label))}
          formatter={(value, name) => {
            const num = typeof value === "number" ? value : Number(value);
            const key = String(name);
            if (key === "spend" || key === "real_cpl") return [fPln(num), key === "spend" ? "Spend" : "Real CPL"];
            return [fInt(num), key === "leads" ? "Leady (real)" : "Bookingi"];
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          formatter={(v) => {
            if (v === "spend") return "Spend";
            if (v === "leads") return "Leady (real)";
            if (v === "real_cpl") return "Real CPL";
            if (v === "bookings") return "Bookingi";
            return v;
          }}
        />
        <Line yAxisId="left" type="monotone" dataKey="spend" stroke="oklch(0.696 0.17 162.48)" strokeWidth={2} dot={false} />
        <Line yAxisId="right" type="monotone" dataKey="leads" stroke="oklch(0.488 0.243 264.376)" strokeWidth={2} dot={false} />
        <Line yAxisId="left" type="monotone" dataKey="real_cpl" stroke="oklch(0.769 0.188 70.08)" strokeWidth={2} strokeDasharray="4 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

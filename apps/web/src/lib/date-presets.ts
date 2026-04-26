/* Date range presets — wartości obliczane wg wybranej tz (default Europe/Warsaw). */

export type RangePreset = "today" | "yesterday" | "7d" | "14d" | "30d" | "custom";

export interface DateRange {
  from: string; // YYYY-MM-DD
  to: string;
}

function toIsoDate(d: Date, tz: string): string {
  // Format YYYY-MM-DD w wybranej tz
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return fmt.format(d);
}

export function rangeForPreset(preset: RangePreset, tz = "Europe/Warsaw"): DateRange {
  const now = new Date();
  const today = toIsoDate(now, tz);
  switch (preset) {
    case "today":
      return { from: today, to: today };
    case "yesterday": {
      const y = new Date(now);
      y.setUTCDate(y.getUTCDate() - 1);
      const yIso = toIsoDate(y, tz);
      return { from: yIso, to: yIso };
    }
    case "7d": {
      const start = new Date(now);
      start.setUTCDate(start.getUTCDate() - 6);
      return { from: toIsoDate(start, tz), to: today };
    }
    case "14d": {
      const start = new Date(now);
      start.setUTCDate(start.getUTCDate() - 13);
      return { from: toIsoDate(start, tz), to: today };
    }
    case "30d": {
      const start = new Date(now);
      start.setUTCDate(start.getUTCDate() - 29);
      return { from: toIsoDate(start, tz), to: today };
    }
    case "custom":
    default:
      return { from: today, to: today };
  }
}

export const PRESET_LABELS: Record<RangePreset, string> = {
  today: "Dziś",
  yesterday: "Wczoraj",
  "7d": "Ostatnie 7 dni",
  "14d": "Ostatnie 14 dni",
  "30d": "Ostatnie 30 dni",
  custom: "Niestandardowy",
};

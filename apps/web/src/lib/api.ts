/* Fetch helper. credentials: 'include' żeby Cloudflare Access cookie szło do api.salespros.app. */
import type {
  AdsetsResponse,
  CampaignsResponse,
  CreativeDetailResponse,
  CreativesResponse,
  FunnelResponse,
  OverviewResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const PREFER_LIVE_DEFAULT = process.env.NEXT_PUBLIC_PREFER_LIVE !== "false";

export interface RangeFilters {
  from: string;
  to: string;
  tz?: string;
  brand?: string;
  status?: string;
  campaign_id?: string;
  prefer_live?: boolean;
}

function buildQuery(filters: RangeFilters): string {
  const p = new URLSearchParams();
  p.set("from", filters.from);
  p.set("to", filters.to);
  if (filters.tz) p.set("tz", filters.tz);
  if (filters.brand && filters.brand !== "all") p.set("brand", filters.brand);
  if (filters.status && filters.status !== "all") p.set("status", filters.status);
  if (filters.campaign_id) p.set("campaign_id", filters.campaign_id);
  const live = filters.prefer_live ?? PREFER_LIVE_DEFAULT;
  if (!live) p.set("prefer_live", "false");
  return p.toString();
}

async function get<T>(path: string, filters: RangeFilters): Promise<T> {
  const url = `${API_BASE}${path}?${buildQuery(filters)}`;
  const res = await fetch(url, {
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  overview: (f: RangeFilters) => get<OverviewResponse>("/api/overview", f),
  campaigns: (f: RangeFilters) => get<CampaignsResponse>("/api/campaigns", f),
  adsets: (f: RangeFilters) => get<AdsetsResponse>("/api/adsets", f),
  creatives: (f: RangeFilters) => get<CreativesResponse>("/api/creatives", f),
  creativeDetail: (ad_id: string, f: RangeFilters) =>
    get<CreativeDetailResponse>(`/api/creatives/${encodeURIComponent(ad_id)}`, f),
  funnel: (f: RangeFilters) => get<FunnelResponse>("/api/funnel", f),
  refresh: async () => {
    const res = await fetch(`${API_BASE}/api/refresh`, {
      method: "POST",
      credentials: "include",
    });
    return res.json();
  },
};

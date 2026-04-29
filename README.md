# Salespros Dashboard

Mózg operacyjny do paid ads Meta + GoHighLevel pipeline. Read-only widok łączący Meta Ads insights z real attribution z GHL contacts.

## Architektura

- **Frontend**: Next.js 15 + Tailwind + shadcn/ui + Recharts → Vercel @ `dashboard.salespros.pl`
- **Backend**: FastAPI + facebook_business SDK → Docker na openclaw VPS @ `api.salespros.app`
- **Auth**: Cloudflare Access (Google email whitelist) chroni oba hosty
- **Networking**: Cloudflare Tunnel z openclaw → zero otwartych portów
- **Data**: live Meta+GHL API z TTLCache 60s; snapshoty z Maca jako fallback

Cała logika atrybucji (Meta `ad_id` ↔ GHL `attributionSource.utmContent`) jest reused z `workspace/marketing/kampanie płatne Salespros/scripts/attribution.py`.

## Local dev

```bash
# Backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # uzupełnij META_ACCESS_TOKEN, GHL_PRIVATE_TOKEN
uvicorn app.main:app --reload --port 8000

# Frontend
cd apps/web
pnpm install
cp .env.example .env.local  # ustaw NEXT_PUBLIC_API_BASE
pnpm dev
```

## Deploy

- Frontend: `git push` → Vercel auto-deploy
- Backend: ssh openclaw → `git pull && docker build -t salespros-dashboard-api . && docker stop... && docker run...`

Pełen plan: `/Users/dawiddziadkowiec/.claude/plans/zbudujmy-dashboard-webowy-do-crystalline-scone.md`

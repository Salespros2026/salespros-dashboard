# Deployment — krok po kroku

## Architektura

```
Browser (Dawid)
   │
   │  https://dashboard.salespros.app  (Vercel CDN, NextAuth Google login)
   ▼
Next.js (Vercel)
   │  server-side fetch z X-API-Key
   ▼
https://api.salespros.app  (Caddy + Let's Encrypt na openclaw)
   │
   ▼
FastAPI :8000 (Docker, network n8n_default)
   │
   ├──► Meta Ads API
   └──► GHL REST API
```

DNS: SEOhost panel — 2 CNAME:
- `dashboard.salespros.app` → `cname.vercel-dns.com`
- `api.salespros.app` → A record `159.69.34.23` (lub CNAME do openclaw hostname)

---

## 1. Google OAuth client (Twoje konto Google)

1. https://console.cloud.google.com → projekt `Salespros Analytics` (lub nowy)
2. **APIs & Services → OAuth consent screen** → External, name: "Salespros Dashboard", support email: dawiddziadkowiec28@gmail.com
3. **Credentials → Create Credentials → OAuth Client ID**
   - Type: Web application
   - Name: `salespros-dashboard`
   - Authorized JavaScript origins:
     - `https://dashboard.salespros.app`
     - `http://localhost:3000` (dev)
   - Authorized redirect URIs:
     - `https://dashboard.salespros.app/api/auth/callback/google`
     - `http://localhost:3000/api/auth/callback/google`
4. Skopiuj `Client ID` → `AUTH_GOOGLE_ID`, `Client Secret` → `AUTH_GOOGLE_SECRET`

## 2. Vercel (frontend)

1. https://vercel.com → Sign up via GitHub
2. **Add New → Project** → import `salespros-dashboard` repo (po pushu z kroku 5)
3. Framework: Next.js (auto-detect), Root Directory: `apps/web`
4. **Environment Variables**:
   ```
   API_BASE                = https://api.salespros.app
   PREFER_LIVE             = true
   DASHBOARD_API_KEY       = <ten sam co w backend .env, openssl rand -hex 32>
   AUTH_SECRET             = <openssl rand -base64 32>
   AUTH_GOOGLE_ID          = <z kroku 1>
   AUTH_GOOGLE_SECRET      = <z kroku 1>
   AUTH_TRUST_HOST         = true
   AUTH_ALLOWED_EMAILS     = dawiddziadkowiec28@gmail.com
   ```
5. **Deploy** → po pierwszym deploy: **Settings → Domains → Add `dashboard.salespros.app`** → Vercel pokaże CNAME do dodania w SEOhost.

## 3. SEOhost DNS (Twoje 2 CNAME)

W panelu SEOhost → DNS dla `salespros.app`:
- Type CNAME, Host `dashboard`, Target `cname.vercel-dns.com.` (Vercel poda dokładny target)
- Type A, Host `api`, Target `159.69.34.23` (IP openclaw)

TTL 3600. Propagacja zwykle <30 min.

## 4. Backend na openclaw

```bash
# A. Z lokalnego Maca — sync repo na VPS
ssh openclaw 'mkdir -p /root/salespros-dashboard /root/salespros-os-snapshots'

rsync -avz --delete \
	--exclude=.venv --exclude=node_modules --exclude=.next \
	--exclude=.git --exclude='.env' --exclude='.env.local' \
	-e "ssh -i ~/.ssh/openclaw" \
	"/Users/dawiddziadkowiec/Salespros OS/dashboard/" \
	root@159.69.34.23:/root/salespros-dashboard/

# B. Skopiuj .env (tokeny + API key)
scp -i ~/.ssh/openclaw \
	"/Users/dawiddziadkowiec/Salespros OS/.env" \
	root@159.69.34.23:/root/salespros-dashboard/apps/api/.env

# Doedytuj na VPS:
ssh openclaw 'cat >> /root/salespros-dashboard/apps/api/.env <<EOF
SNAPSHOTS_DIR=/app/snapshots
REQUIRE_API_KEY=true
DASHBOARD_API_KEY=<ten sam co w Vercel>
CORS_ALLOW_ORIGINS=https://dashboard.salespros.app
EOF'

# C. Pierwszy snapshot sync
rsync -avz --exclude='*.bak.*' \
	-e "ssh -i ~/.ssh/openclaw" \
	"/Users/dawiddziadkowiec/Salespros OS/workspace/marketing/kampanie płatne Salespros/snapshots/" \
	root@159.69.34.23:/root/salespros-os-snapshots/

# D. Deploy (build + run + Caddy)
ssh openclaw 'bash /root/salespros-dashboard/deploy/openclaw-deploy.sh'

# E. Verify
ssh openclaw 'docker logs --tail 20 salespros-dashboard-api'
curl https://api.salespros.app/healthz   # → {"status":"ok"}
```

## 5. Cron rsync snapshotów (na lokalnym Macu)

Edytuj `workspace/marketing/kampanie płatne Salespros/scripts/daily_run.sh` —
dodaj na końcu:

```bash
# Sync snapshotów na openclaw (production dashboard backend)
rsync -avz --exclude='*.bak.*' \
	-e "ssh -i $HOME/.ssh/openclaw" \
	"$WORKSPACE/snapshots/" \
	root@159.69.34.23:/root/salespros-os-snapshots/ || true
```

## 6. Smoke check

1. Otwórz `https://dashboard.salespros.app` w incognito → redirect na `/login`
2. Klik "Zaloguj przez Google" → Google OAuth → zgadzasz na consent → wracasz na dashboard
3. Sprawdź: KPI cards, real CPL ≠ Meta CPL, kampanie GAWRONIFY/Salespros split, klik na kreację → drill-down z listą leadów GHL
4. Klik leada → otwiera `app.gohighlevel.com/v2/...` z kontaktem

## Troubleshooting

| Problem | Fix |
|---|---|
| 502 Backend unreachable | `ssh openclaw 'docker logs salespros-dashboard-api'` — sprawdź czy działa, czy ma .env |
| 401 Unauthorized | Sprawdź czy `DASHBOARD_API_KEY` w Vercel = ten z backend .env |
| Login zwraca 403 | Email Google nie na `AUTH_ALLOWED_EMAILS` lista |
| SSL pending api.salespros.app | DNS A record nie propagowany — `dig +short api.salespros.app` powinno zwrócić 159.69.34.23 |
| Liczby się nie zgadzają z markdown raportem | Sprawdź TZ selector — Europe/Warsaw vs lokalny Mac |

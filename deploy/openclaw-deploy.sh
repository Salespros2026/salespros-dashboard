#!/bin/bash
# Deploy salespros-dashboard backend na openclaw VPS.
# Uruchamiać Z openclaw (po SSH), nie lokalnie.
#
# Pierwsze uruchomienie:
#   ssh openclaw 'mkdir -p /root/salespros-dashboard'
#   rsync -avz --exclude=.venv --exclude=node_modules --exclude=.next \
#     -e "ssh -i ~/.ssh/openclaw" \
#     "/Users/dawiddziadkowiec/Salespros OS/dashboard/" \
#     root@159.69.34.23:/root/salespros-dashboard/
#   ssh openclaw 'bash /root/salespros-dashboard/deploy/openclaw-deploy.sh'
#
# Następne deploye:
#   git push (z lokalnego)
#   ssh openclaw 'cd /root/salespros-dashboard && git pull && bash deploy/openclaw-deploy.sh'

set -euo pipefail

cd /root/salespros-dashboard

# Sprawdź wymagane env files
if [[ ! -f /root/salespros-dashboard/apps/api/.env ]]; then
	echo "ERROR: brak /root/salespros-dashboard/apps/api/.env — skopiuj .env.example i uzupełnij"
	exit 1
fi
if [[ ! -f /root/salespros-dashboard/apps/web/.env.production ]]; then
	echo "ERROR: brak /root/salespros-dashboard/apps/web/.env.production — skopiuj .env.production.example i uzupełnij"
	exit 1
fi

# ===== API =====
echo "=== Building API image ==="
docker build -t salespros-dashboard-api:latest ./apps/api

docker stop salespros-dashboard-api 2>/dev/null || true
docker rm salespros-dashboard-api 2>/dev/null || true

# Persistent data dir dla classification kampanii (CPL split ACQ/RTG).
DATA_DIR=/var/lib/salespros-dashboard/data
mkdir -p "$DATA_DIR"
if [[ ! -f "$DATA_DIR/campaign_classification.json" ]] && \
   [[ -f /root/salespros-dashboard/apps/api/data/campaign_classification.json ]]; then
	echo "=== Seeding classification volume from repo ==="
	cp /root/salespros-dashboard/apps/api/data/campaign_classification.json "$DATA_DIR/"
fi

echo "=== Starting API container ==="
docker run -d \
	--name salespros-dashboard-api \
	--restart always \
	--network n8n_default \
	-v /root/salespros-os-snapshots:/app/snapshots:ro \
	-v "$DATA_DIR":/app/data \
	--env-file /root/salespros-dashboard/apps/api/.env \
	salespros-dashboard-api:latest

# ===== WEB =====
echo "=== Building WEB image (może zająć 2-4 min — Next.js build) ==="
docker build -t salespros-dashboard-web:latest ./apps/web

docker stop salespros-dashboard-web 2>/dev/null || true
docker rm salespros-dashboard-web 2>/dev/null || true

echo "=== Starting WEB container ==="
docker run -d \
	--name salespros-dashboard-web \
	--restart always \
	--network n8n_default \
	--env-file /root/salespros-dashboard/apps/web/.env.production \
	salespros-dashboard-web:latest

# ===== Caddy reload =====
# Caddy chodzi niezależnie z n8n stacku, mount /root/n8n/Caddyfile.
# Edycja config: ssh openclaw, vim /root/n8n/Caddyfile, ten skrypt reloaduje.
if docker ps --format '{{.Names}}' | grep -q '^caddy$'; then
	echo "=== Reloading Caddy config ==="
	docker exec caddy caddy reload --config /etc/caddy/Caddyfile || \
		echo "WARN: Caddy reload failed (config może być invalid). Sprawdź: docker exec caddy caddy validate --config /etc/caddy/Caddyfile"
else
	echo "WARN: Caddy nie chodzi. Web container będzie dostępny tylko wewnątrz n8n_default network."
fi

echo "=== Deploy complete ==="
echo "Logs API: docker logs -f salespros-dashboard-api"
echo "Logs WEB: docker logs -f salespros-dashboard-web"
echo "Logs Caddy: docker logs -f caddy"
echo "Health API:  curl https://api.salespros.pl/healthz"
echo "Health WEB:  curl -I https://dashboard.salespros.pl/login (po DNS prop)"

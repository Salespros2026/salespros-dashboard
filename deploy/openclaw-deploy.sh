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

# 1. Build API image
echo "=== Building API image ==="
docker build -t salespros-dashboard-api:latest ./apps/api

# 2. Stop + remove old container (jeśli istnieje)
docker stop salespros-dashboard-api 2>/dev/null || true
docker rm salespros-dashboard-api 2>/dev/null || true

# 3. Sprawdź czy .env istnieje
if [[ ! -f /root/salespros-dashboard/apps/api/.env ]]; then
	echo "ERROR: brak /root/salespros-dashboard/apps/api/.env — skopiuj .env.example i uzupełnij"
	exit 1
fi

# 4. Run new API container
echo "=== Starting API container ==="
docker run -d \
	--name salespros-dashboard-api \
	--restart always \
	--network n8n_default \
	-v /root/salespros-os-snapshots:/app/snapshots:ro \
	--env-file /root/salespros-dashboard/apps/api/.env \
	salespros-dashboard-api:latest

# 5. Caddy (tylko pierwsze uruchomienie — sprawdź czy już działa)
if ! docker ps --format '{{.Names}}' | grep -q '^caddy$'; then
	echo "=== Starting Caddy reverse proxy ==="
	docker run -d \
		--name caddy \
		--restart always \
		--network n8n_default \
		-p 80:80 -p 443:443 \
		-v /root/salespros-dashboard/deploy/Caddyfile:/etc/caddy/Caddyfile:ro \
		-v caddy_data:/data \
		-v caddy_config:/config \
		caddy:2-alpine
else
	echo "=== Caddy already running, reload config ==="
	docker exec caddy caddy reload --config /etc/caddy/Caddyfile
fi

echo "=== Deploy complete ==="
echo "Logs API:  docker logs -f salespros-dashboard-api"
echo "Logs Caddy: docker logs -f caddy"
echo "Health: curl https://api.salespros.app/healthz"

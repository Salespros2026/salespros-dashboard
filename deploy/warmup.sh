#!/bin/bash
# Cron warmup — utrzymuje cache backendu hot, żeby user nigdy nie trafiał na cold call.
# Hituje top 6 najczęstszych kombinacji filter (overview/campaigns × dziś/7d/30d × all/gawronify).
# Cache TTL w aggregation.py: lite 5min, full 15min, historical 1h.
#
# Crontab: */5 * * * * bash /root/salespros-dashboard/deploy/warmup.sh > /tmp/warmup.log 2>&1

set -euo pipefail

API_BASE="http://salespros-dashboard-api:8000"
ENV_FILE="/root/salespros-dashboard/apps/api/.env"
if [[ ! -f "$ENV_FILE" ]]; then
	echo "WARN: brak $ENV_FILE — skip warmup"
	exit 0
fi
API_KEY=$(grep ^DASHBOARD_API_KEY "$ENV_FILE" | cut -d= -f2)

TODAY=$(date -u +%Y-%m-%d)
WEEK_AGO=$(date -u -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v -7d +%Y-%m-%d)
MONTH_AGO=$(date -u -d "30 days ago" +%Y-%m-%d 2>/dev/null || date -v -30d +%Y-%m-%d)

# Helper: hituje przez sieć Docker n8n_default (ten sam co Caddy).
# Używamy wgeta z n8n containera (curl nie ma w obrazach :alpine bez extra install).
hit() {
	local path="$1"
	local label="$2"
	local t_start t_end
	t_start=$(date +%s.%N)
	docker exec n8n wget -qO /dev/null \
		--header="X-API-Key: $API_KEY" \
		--tries=1 --timeout=60 \
		"$API_BASE$path" 2>/dev/null && \
		t_end=$(date +%s.%N) && \
		echo "$(date +%H:%M:%S) ✓ $label ($(awk -v s="$t_start" -v e="$t_end" 'BEGIN{printf "%.1fs", e-s}'))" || \
		echo "$(date +%H:%M:%S) ✗ $label FAILED"
}

# Top 6 kombinacji — pokrywa większość ruchu user'a.
hit "/api/overview?from=$TODAY&to=$TODAY&brand=all" "overview-today-all"
hit "/api/overview?from=$WEEK_AGO&to=$TODAY&brand=all" "overview-7d-all"
hit "/api/overview?from=$WEEK_AGO&to=$TODAY&brand=gawronify" "overview-7d-gawronify"
hit "/api/campaigns?from=$WEEK_AGO&to=$TODAY&brand=all" "campaigns-7d-all"
hit "/api/campaigns?from=$MONTH_AGO&to=$TODAY&brand=all" "campaigns-30d-all"
hit "/api/admin/campaigns" "admin-campaigns"

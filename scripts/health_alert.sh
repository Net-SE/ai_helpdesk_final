#!/usr/bin/env sh
set -eu

URL="${HEALTH_URL:-http://127.0.0.1:8000/core/healthz/}"
ALERT_COMMAND="${ALERT_COMMAND:-}"

if curl --fail --silent --show-error --max-time 10 "$URL" >/tmp/helpdesk_health.json; then
  echo "Health check OK: $(cat /tmp/helpdesk_health.json)"
  exit 0
fi

echo "Health check FAILED: $URL" >&2
if [ -n "$ALERT_COMMAND" ]; then
  sh -c "$ALERT_COMMAND"
fi
exit 1

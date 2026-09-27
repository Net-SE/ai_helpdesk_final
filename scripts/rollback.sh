#!/usr/bin/env sh
set -eu

TAG="${1:?Usage: ./scripts/rollback.sh <image-tag>}"
IMAGE="${IMAGE_NAME:-ghcr.io/example/ai-helpdesk}"

echo "Rolling back to ${IMAGE}:${TAG}"
export HELP_DESK_IMAGE="${IMAGE}:${TAG}"

docker compose -f docker-compose.staging.yml pull web
docker compose -f docker-compose.staging.yml up -d web

python scripts/smoke_test.py "${STAGING_URL:-http://127.0.0.1:8001}"

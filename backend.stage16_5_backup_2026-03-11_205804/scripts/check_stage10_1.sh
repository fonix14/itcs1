#!/usr/bin/env bash
set -euo pipefail

echo "===== docker compose ps ====="
docker compose -f docker-compose.yml -f docker-compose.minio.yml ps

echo
echo "===== minio health ====="
curl -fsS http://localhost:9000/minio/health/live && echo

echo
echo "===== api mobile tasks ====="
curl -fsS http://localhost:8080/api/mobile/tasks && echo

echo
echo "===== attachments check ====="
TASK_ID=$(docker exec backend-db-1 psql -U itcs -d itcs -Atqc "select id::text from tasks limit 1;" || true)

if [ -n "${TASK_ID:-}" ]; then
  echo "Using task id: $TASK_ID"
  curl -fsS "http://localhost:8080/api/tasks/$TASK_ID/attachments" && echo
else
  echo "No tasks found in DB"
fi

echo
echo "===== minio bucket list ====="
docker compose -f docker-compose.yml -f docker-compose.minio.yml logs minio-mc-init --tail=50 || true

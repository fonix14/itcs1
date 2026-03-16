#!/usr/bin/env bash

set +e

PROJECT_DIR="/opt/itcs/itcs_mvp_stage4/backend"
DB_CONTAINER="backend-db-1"
API_URL="http://localhost:8080"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

section() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

cd "$PROJECT_DIR" || {
  echo "Cannot cd to $PROJECT_DIR"
  exit 1
}

section "ITCS DOCTOR :: BASIC PATHS"

[ -d "$PROJECT_DIR" ] && ok "Project dir exists: $PROJECT_DIR" || err "Project dir missing"
[ -f "$PROJECT_DIR/docker-compose.yml" ] && ok "docker-compose.yml found" || err "docker-compose.yml missing"
[ -f "$PROJECT_DIR/requirements.txt" ] && ok "requirements.txt found" || warn "requirements.txt missing"
[ -f "$PROJECT_DIR/app/main.py" ] && ok "app/main.py found" || err "app/main.py missing"
[ -f "$PROJECT_DIR/app/ui.py" ] && ok "app/ui.py found" || warn "app/ui.py missing"
[ -f "$PROJECT_DIR/app/api/portal_l4_uploads.py" ] && ok "portal_l4_uploads.py found" || warn "portal_l4_uploads.py missing"
[ -f "$PROJECT_DIR/app/services/portal_l4_parser.py" ] && ok "portal_l4_parser.py found" || warn "portal_l4_parser.py missing"

section "ITCS DOCTOR :: DOCKER COMPOSE STATUS"

docker compose ps
if [ $? -eq 0 ]; then
  ok "docker compose ps completed"
else
  err "docker compose ps failed"
fi

section "ITCS DOCTOR :: API HTTP CHECKS"

curl -fsS "$API_URL/docs" >/dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "API /docs reachable"
else
  err "API /docs not reachable"
fi

curl -fsS "$API_URL/ui" >/dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "UI /ui reachable"
else
  warn "UI /ui not reachable"
fi

curl -fsS "$API_URL/ui/ops" >/dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "UI /ui/ops reachable"
else
  warn "UI /ui/ops not reachable"
fi

curl -fsS "$API_URL/openapi.json" >/dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "API openapi.json reachable"
else
  warn "API openapi.json not reachable"
fi

section "ITCS DOCTOR :: API CONTAINER LOGS"

docker compose logs api --tail=80

section "ITCS DOCTOR :: NOTIFIER CONTAINER LOGS"

docker compose logs notifier --tail=80

section "ITCS DOCTOR :: PYTHON PACKAGE CHECK INSIDE API"

docker compose exec -T api python - << 'PY'
mods = ["fastapi", "uvicorn", "sqlalchemy", "asyncpg", "pandas", "openpyxl"]
for m in mods:
    try:
        __import__(m)
        print(f"[OK] python module available: {m}")
    except Exception as e:
        print(f"[ERR] python module missing: {m} :: {e}")
PY

section "ITCS DOCTOR :: ROUTE CHECKS IN CODE"

grep -R 'portal_l4_uploads' -n app 2>/dev/null
grep -R '@router.post("/portal_l4_uploads")' -n app 2>/dev/null
grep -R '@router.post("/upload_excel")' -n app 2>/dev/null
grep -R 'process_excel_upload' -n app 2>/dev/null

section "ITCS DOCTOR :: DB CONNECTIVITY"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "SELECT now();" 2>/dev/null
if [ $? -eq 0 ]; then
  ok "DB connection ok"
else
  err "DB connection failed"
fi

section "ITCS DOCTOR :: DB TABLE COUNTS"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT 'uploads' AS table_name, count(*) FROM uploads
UNION ALL
SELECT 'tasks', count(*) FROM tasks
UNION ALL
SELECT 'import_errors', count(*) FROM import_errors
UNION ALL
SELECT 'anomalies', count(*) FROM anomalies
UNION ALL
SELECT 'notification_outbox', count(*) FROM notification_outbox
ORDER BY table_name;
" 2>/dev/null

section "ITCS DOCTOR :: LAST UPLOADS"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT id, file_name, profile_id, uploaded_at, total_rows, valid_rows, invalid_rows, invalid_ratio, seen_tasks_count
FROM uploads
ORDER BY uploaded_at DESC
LIMIT 10;
" 2>/dev/null

section "ITCS DOCTOR :: LAST IMPORT ERRORS"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT upload_id, row_number, error, created_at
FROM import_errors
ORDER BY created_at DESC
LIMIT 20;
" 2>/dev/null

section "ITCS DOCTOR :: TASKS HEALTH"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT
  count(*) AS total_tasks,
  count(*) FILTER (WHERE status = 'open') AS open_tasks,
  count(*) FILTER (WHERE status = 'resolved') AS resolved_tasks,
  count(*) FILTER (WHERE sla_due_at IS NOT NULL AND sla_due_at < now() AND status <> 'resolved') AS overdue_tasks
FROM tasks;
" 2>/dev/null

section "ITCS DOCTOR :: LAST SEEN TASKS"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT portal_task_id, status, last_seen_at
FROM tasks
ORDER BY last_seen_at DESC NULLS LAST
LIMIT 20;
" 2>/dev/null

section "ITCS DOCTOR :: NOTIFICATION QUEUE"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT template, status, count(*)
FROM notification_outbox
GROUP BY template, status
ORDER BY template, status;
" 2>/dev/null

section "ITCS DOCTOR :: RECENT NOTIFICATION ROWS"

docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "
SELECT template, status, created_at, sent_at
FROM notification_outbox
ORDER BY created_at DESC
LIMIT 20;
" 2>/dev/null

section "ITCS DOCTOR :: DOCKER COMPOSE CONFIG CHECK"

docker compose config >/dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "docker compose config valid"
else
  err "docker compose config invalid"
fi

section "ITCS DOCTOR :: UVICORN TARGET CHECK"

grep -R "uvicorn" -n docker-compose.yml Dockerfile 2>/dev/null

section "ITCS DOCTOR :: FINISH"

echo
echo "Doctor finished."
echo "If upload still fails, send me output of:"
echo "bash /opt/itcs/itcs_mvp_stage4/backend/scripts/itcs_doctor.sh > /opt/itcs/itcs_doctor_report.txt 2>&1"
echo "tail -n 200 /opt/itcs/itcs_doctor_report.txt"

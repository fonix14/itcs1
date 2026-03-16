#!/usr/bin/env bash

set -e

PROJECT_ROOT="/opt/itcs/itcs_mvp_stage4"
BACKEND_DIR="/opt/itcs/itcs_mvp_stage4/backend"
SQL_FILE="/opt/itcs/itcs_mvp_stage4/backend/sql/0001_itcs_schema.sql"
DB_CONTAINER="backend-db-1"

echo "============================================================"
echo "ITCS REPAIR :: START"
echo "============================================================"

cd "$BACKEND_DIR"

echo
echo "[1/8] CHECK PROJECT PATHS"
test -d "$PROJECT_ROOT"
test -d "$BACKEND_DIR"
echo "[OK] project paths found"

echo
echo "[2/8] APPLY BASE SCHEMA IF EXISTS"
if [ -f "$SQL_FILE" ]; then
  cat "$SQL_FILE" | docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs
  echo "[OK] base schema applied"
else
  echo "[WARN] schema file not found: $SQL_FILE"
fi

echo
echo "[3/8] CREATE MISSING SERVICE TABLES"
docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs << 'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS import_errors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id uuid,
    row_number integer,
    error text,
    raw jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_import_errors_upload_id
    ON import_errors(upload_id);

CREATE INDEX IF NOT EXISTS idx_import_errors_created_at
    ON import_errors(created_at DESC);

CREATE TABLE IF NOT EXISTS upload_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id uuid NOT NULL,
    baseline_seen integer,
    abs_drop integer,
    rel_drop numeric(10,2),
    coverage_drop boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_upload_metrics_upload_id
    ON upload_metrics(upload_id);

CREATE INDEX IF NOT EXISTS idx_upload_metrics_created_at
    ON upload_metrics(created_at DESC);

CREATE TABLE IF NOT EXISTS anomalies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id uuid,
    task_id uuid,
    store_id uuid,
    type text NOT NULL,
    severity text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'open',
    due_at timestamptz,
    meta jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_anomalies_status
    ON anomalies(status);

CREATE INDEX IF NOT EXISTS idx_anomalies_created_at
    ON anomalies(created_at DESC);

CREATE TABLE IF NOT EXISTS task_internal_state (
    task_id uuid PRIMARY KEY,
    accepted_at timestamptz,
    accepted_by uuid,
    comment text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    endpoint text NOT NULL,
    p256dh text,
    auth text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS health_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trust_level text NOT NULL,
    last_import_at timestamptz,
    invalid_ratio numeric(10,4),
    pending_anomalies integer NOT NULL DEFAULT 0,
    overdue_critical_anomalies integer NOT NULL DEFAULT 0,
    overdue_tasks integer NOT NULL DEFAULT 0,
    no_import_hours integer NOT NULL DEFAULT 0,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sla_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid NOT NULL,
    event_type text NOT NULL,
    details jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    metric text NOT NULL,
    value numeric,
    payload jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
SQL
echo "[OK] missing service tables ensured"

echo
echo "[4/8] SEED BASIC USERS/STORES"
docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs << 'SQL'
INSERT INTO users (id, full_name, email, role, is_active)
VALUES
('11111111-1111-1111-1111-111111111111', 'Dispatcher', 'dispatcher@local', 'dispatcher', true),
('22222222-2222-2222-2222-222222222222', 'Manager 1', 'manager1@local', 'manager', true)
ON CONFLICT (email) DO NOTHING;

INSERT INTO stores (store_no, name, address, assigned_user_id, is_active)
VALUES
('1001', 'Store 1001', 'Address 1001', '22222222-2222-2222-2222-222222222222', true)
ON CONFLICT (store_no) DO NOTHING;
SQL
echo "[OK] basic seed applied"

echo
echo "[5/8] ENSURE PYTHON REQUIREMENTS"
touch requirements.txt
grep -qxF 'pandas' requirements.txt || echo 'pandas' >> requirements.txt
grep -qxF 'openpyxl' requirements.txt || echo 'openpyxl' >> requirements.txt
echo "[OK] requirements updated"

echo
echo "[6/8] CHECK UVICORN TARGET"
if grep -q 'uvicorn main:app' docker-compose.yml; then
  sed -i 's|uvicorn main:app|uvicorn app.main:app|g' docker-compose.yml
  echo "[OK] docker-compose uvicorn target fixed"
else
  echo "[OK] uvicorn target already looks fine"
fi

echo
echo "[7/8] REBUILD AND RESTART"
docker compose down
docker compose up -d --build
sleep 5
docker compose ps
echo "[OK] containers rebuilt"

echo
echo "[8/8] FINAL CHECKS"
docker compose logs api --tail=80 || true
docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "\dt" || true
docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "SELECT id, full_name, email, role FROM users ORDER BY created_at;" || true
docker exec -i "$DB_CONTAINER" psql -U itcs -d itcs -c "SELECT store_no, name, assigned_user_id FROM stores ORDER BY store_no;" || true

if [ -f "$BACKEND_DIR/scripts/itcs_doctor.sh" ]; then
  echo
  echo "RUN DOCTOR..."
  bash "$BACKEND_DIR/scripts/itcs_doctor.sh" || true
else
  echo "[WARN] doctor script not found, skipped"
fi

echo
echo "============================================================"
echo "ITCS REPAIR :: DONE"
echo "============================================================"

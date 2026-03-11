ITCS Stage 8 — SLA Control

Что добавляет:
- SLA overdue detection
- SLA risk (<24h)
- manager workload metrics
- API:
  - /api/dashboard
  - /api/dashboard/health
  - /api/dashboard/sla
- UI:
  - /ui/dashboard

Установка:
cd /opt/itcs/itcs_mvp_stage4/backend
unzip /opt/itcs/itcs_stage8_sla_control.zip
python3 scripts/patch_main_stage8.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

Проверка:
curl http://localhost:8080/api/dashboard/sla
curl http://localhost:8080/ui/dashboard

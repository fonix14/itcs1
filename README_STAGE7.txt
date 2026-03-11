ITCS Stage 7 — Ops Dashboard

Что внутри:
- app/api/dashboard.py
- app/services/dashboard_service.py
- app/ui_dashboard.py
- app/templates/dashboard.html
- app/static/dashboard.js
- scripts/patch_main_stage7.py

Установка:
1) Загрузить архив на сервер
2) Распаковать в /opt/itcs/itcs_mvp_stage4/backend
3) Запустить patch script
4) Перезапустить api в dev-режиме или обычном режиме

Команды:

cd /opt/itcs/itcs_mvp_stage4/backend
unzip /opt/itcs/itcs_stage7_ops_dashboard.zip
python3 scripts/patch_main_stage7.py

# dev mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

# или обычный режим
docker compose build api
docker compose up -d api

Проверка:
curl http://localhost:8080/api/dashboard
curl http://localhost:8080/api/dashboard/health
curl http://localhost:8080/ui/dashboard

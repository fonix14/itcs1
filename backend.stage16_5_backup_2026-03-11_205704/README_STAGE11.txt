ITCS Stage 11 — Manager Auth + Store Isolation

Что добавляет:
- простую header-based авторизацию для manager / dispatcher
- manager видит только свои магазины
- dispatcher видит всё
- mobile portal / API работают с фильтрацией по actor
- endpoints:
  - GET  /api/mobile/me
  - GET  /api/mobile/tasks
  - GET  /api/mobile/tasks/{task_id}
  - POST /api/mobile/tasks/{task_id}/accept
  - POST /api/mobile/tasks/{task_id}/comment
  - GET  /m/tasks
  - GET  /m/task/{task_id}

Как работает:
- actor передается в headers:
  X-User-Id: <UUID пользователя>
  X-User-Role: manager | dispatcher
- dispatcher видит все задачи
- manager видит только задачи магазинов, где stores.assigned_user_id = X-User-Id

Установка:
cd /opt/itcs/itcs_mvp_stage4/backend
unzip /opt/itcs/itcs_stage11_manager_auth_storeisolation.zip
python3 scripts/patch_main_stage11.py
docker compose restart api

Проверка:
curl -H "X-User-Id: <MANAGER_UUID>" -H "X-User-Role: manager" http://localhost:8080/api/mobile/me
curl -H "X-User-Id: <MANAGER_UUID>" -H "X-User-Role: manager" http://localhost:8080/api/mobile/tasks
curl -H "X-User-Id: <DISPATCHER_UUID>" -H "X-User-Role: dispatcher" http://localhost:8080/api/mobile/tasks

Важно:
- это MVP auth layer, без пароля и без JWT
- подходит для внутреннего портала и reverse proxy auth

ITCS Stage 10.2 — Mobile Manager Portal

Что добавляет:
- улучшенный mobile manager portal
- /m/tasks — список карточек с фильтрами
- /m/task/{task_id} — карточка задачи
- фото-галерея
- кнопки: Принял, Обновить, Сохранить комментарий, Загрузить фото
- PWA manifest + service worker
- mobile bottom nav

Установка:
cd /opt/itcs/itcs_mvp_stage4/backend
unzip /opt/itcs/itcs_stage10_2_mobile_manager_portal.zip
python3 scripts/patch_main_stage10_2.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

Проверка:
curl http://localhost:8080/m/tasks
curl http://localhost:8080/m/task/<TASK_UUID>

Открывать:
http://SERVER:8080/m/tasks

Важно:
- Stage10.2 использует уже существующие API Stage10:
  /api/mobile/tasks
  /api/mobile/tasks/{task_id}
  /api/mobile/tasks/{task_id}/accept
  /api/mobile/tasks/{task_id}/comment
  /api/tasks/{task_id}/attachments
- Для реальной загрузки фото MinIO и minio python package должны уже работать.

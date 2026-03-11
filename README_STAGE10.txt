ITCS Stage 10 — Mobile Manager + Photo MVP

Что добавляет:
- mobile manager UI:
  - /m/tasks
  - /m/task/{task_id}
- photo attachments:
  - POST /api/tasks/{task_id}/attachments
  - GET  /api/tasks/{task_id}/attachments
- MinIO integration
- SQL migration template for task_attachments

Установка:
1) cd /opt/itcs/itcs_mvp_stage4/backend
2) unzip /opt/itcs/itcs_stage10_mobile_manager_photo_mvp.zip
3) применить SQL:
   docker exec -i backend-db-1 psql -U itcs -d itcs < sql/stage10_task_attachments.sql
4) добавить env в docker compose / .env:
   MINIO_ENDPOINT=minio:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   MINIO_BUCKET=itcs
   MINIO_SECURE=false
5) python3 scripts/patch_main_stage10.py
6) docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

Проверка:
- curl http://localhost:8080/m/tasks
- curl http://localhost:8080/api/tasks/1/attachments
- открыть:
  http://SERVER:8080/m/tasks

Важно:
- если MinIO пока не поднят, API загрузки фото вернёт ошибку подключения
- mobile UI routes вынесены в /m/*, чтобы не ломать существующий /ui/*

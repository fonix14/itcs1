ITCS Stage 9 — Task Control UI

Что добавляет:
- /api/tasks
- /api/tasks/{task_id}
- /api/tasks/{task_id}/comment
- /api/tasks/{task_id}/accept
- /ui/tasks
- /ui/task/{task_id}

Функции:
- список заявок
- карточка заявки
- фильтр overdue
- комментарий
- кнопка "Принял"

Установка:
cd /opt/itcs/itcs_mvp_stage4/backend
unzip /opt/itcs/itcs_stage9_task_control_ui.zip
python3 scripts/patch_main_stage9.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api

Проверка:
curl http://localhost:8080/api/tasks
curl http://localhost:8080/ui/tasks

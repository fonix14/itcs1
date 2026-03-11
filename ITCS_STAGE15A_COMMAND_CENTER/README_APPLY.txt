ITCS_STAGE15A_COMMAND_CENTER

Что внутри:
- backend/app/api/command_center.py
- backend/app/ui_command_center.py
- backend/app/static/command_center.js
- backend/app/static/command_center.css
- backend/db/sql/stage15a_command_center.sql
- backend/patches/main.py.patch.txt

Как применить на сервере:

cd /opt/itcs/itcs_mvp_stage4/backend

# 1. Создать резервную копию main.py
cp app/main.py app/main.py.bak_stage15a_$(date +%F_%H%M%S)

# 2. Скопировать новые файлы
# backend/app/api/command_center.py              -> app/api/command_center.py
# backend/app/ui_command_center.py               -> app/ui_command_center.py
# backend/app/static/command_center.js           -> app/static/command_center.js
# backend/app/static/command_center.css          -> app/static/command_center.css

# 3. Применить SQL
# пример через docker compose exec db psql, либо любым рабочим способом в вашей инсталляции
# psql -U itcs -d itcs -f backend/db/sql/stage15a_command_center.sql

# 4. Внести 2 импорта и 2 include_router в app/main.py
# см. backend/patches/main.py.patch.txt

# 5. Пересобрать API
# docker compose up -d --build api

# 6. Проверка
# curl -s http://localhost:8080/api/command-center/overview | python -m json.tool
# curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/ui/command-center

Целевые URL:
- /ui/command-center
- /api/command-center/overview

Примечание:
API написан максимально мягко: если таблицы platform_* ещё не созданы или какие-то поля в uploads/tasks отличаются,
роут вернёт fallback-данные и не должен ломать портал.

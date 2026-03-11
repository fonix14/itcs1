ITCS Stage 10.1 — MinIO Storage Layer

Что добавляет:
- docker-compose.minio.yml
- .env.minio.example
- scripts/minio_mc_init.sh
- scripts/patch_requirements_minio.sh
- scripts/check_stage10_1.sh

Назначение:
- поднять MinIO + web console
- автоматически создать bucket itcs
- подготовить backend к работе с фото

Установка:

cd /opt/itcs/itcs_mvp_stage4/backend

unzip /opt/itcs/itcs_stage10_1_minio_storage.zip

cp .env.minio.example .env.minio
nano .env.minio

bash scripts/patch_requirements_minio.sh

docker compose build api

docker compose -f docker-compose.yml -f docker-compose.minio.yml --env-file .env.minio up -d

bash scripts/check_stage10_1.sh

После этого:
- MinIO API:     http://SERVER:9000
- MinIO Console: http://SERVER:9001
- Mobile UI:     http://SERVER:8080/m/tasks

Важно:
- если у тебя уже занят 9000 или 9001, измени порты в docker-compose.minio.yml
- если не хочешь держать env в отдельном файле, перенеси переменные в основной .env

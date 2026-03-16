# ITCS — Stage 4 (Matrix Notification Engine)

Stage 1–3 уже закрыты. Этот пакет добавляет **Stage 4: Notification Engine**.

## Что делает Stage 4

- ✅ После каждого успешного импорта (upload) — **ровно 1 дайджест** в Matrix room “Заявки”
- ✅ Daily health — **макс 1 сообщение в сутки** и только при деградации (YELLOW/RED)
- ✅ Идемпотентность:
  - DB dedupe: `dedupe_key` (unique)
  - Matrix dedupe: `txnId = outbox_id`
- ✅ Ретраи с backoff до 10 попыток → потом `dead`
- ✅ Отдельный контейнер `notifier` (poller loop), **без Celery/Redis**
- ✅ Health API для диспетчера: `/api/notifications/health`

---

## Быстрый старт

```bash
cd /opt/itcs
unzip itcs_mvp_stage4.zip
cd itcs_mvp_stage4/backend
cp .env.example .env

# Заполни MATRIX_ACCESS_TOKEN и MATRIX_ROOM_ID в .env

docker compose down -v --remove-orphans || true
docker compose up -d --build

docker compose exec api bash -lc "alembic upgrade head"
docker compose exec api bash -lc "python -m app.scripts.seed_demo"
```

---

## Как получить MATRIX_ACCESS_TOKEN

Самый простой способ (через Element Web):

1) Открой Element Web (например, chat.m-clining.ru)
2) В DevTools (F12) → Application/Storage → Local Storage
3) Найди ключи вида `mx_access_token` или похожие.

Альтернатива (через login API) — можно добавить позже.

---

## Как получить MATRIX_ROOM_ID (room_id вида !abc:server)

В комнате открой "Room settings" → "Advanced" / "Room info" → Room ID.

---

## Проверка работоспособности

### 1) Импорт

`POST /api/uploads` (dispatcher)

После успешного commit создаётся 1 запись в `notification_outbox` и notifier отправляет 1 сообщение.

### 2) Health очереди

`GET /api/notifications/health` (dispatcher)

Показывает:
- queued/failed/dead
- last_tick_at / last_sent_at
- worker_alive

### 3) Логи

```bash
docker compose logs -f --tail=200 notifier
```

---

## Definition of Done

- XLSX импортится → в комнате “Заявки” появляется 1 digest
- Повторный запуск notifier не создаёт дубль
- При недоступности Matrix → ретраи, статус/ошибка видны в health
- Есть `/api/notifications/health` (dispatcher only)

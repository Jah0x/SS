# Subs MVP (Watcher + API)

- Watcher читает все реплики ConfigMap с UID и складывает в Postgres (таблицы из миграций).
- API (внутренний): выдача/отзыв UID по логину, статус UID.
- Источник истины по пулу UID — ConfigMap (read-only).

## Требования
- Применены миграции из архива **subs-db-kit** (таблицы `pools`, `uids`, `uid_assignments`, `uid_sources`, функции `subs_*`).
- K8s с доступом к ConfigMap'ам в `securelink`.
- Postgres доступен по `DB_DSN`.

## Сборка и деплой
```bash
docker build -t ghcr.io/your-org/subs:0.1.0 .
# docker push ghcr.io/your-org/subs:0.1.0

kubectl -n securelink apply -f k8s/rbac.yaml
kubectl -n securelink apply -f k8s/secret.example.yaml   # отредактируй перед этим
kubectl -n securelink apply -f k8s/deployment.yaml
# (опц.) kubectl -n securelink apply -f k8s/networkpolicy.yaml
```

## Миграции БД
```bash
# применить миграции (из корня репозитория) и дождаться завершения Job
kubectl apply -k ../k8s
kubectl -n securelink wait --for=condition=complete job/subs-migrate --timeout=120s

# после успешных миграций деплой сервиса
kubectl -n securelink apply -f k8s/deployment.yaml
```

## Переменные окружения

Сервис использует следующие переменные окружения:

- `DB_DSN` — строка подключения к Postgres.
- `SUBS_INTERNAL_TOKEN` — токен для внутренней аутентификации.
- `SUBS_DOMAIN` — домен, указывающий на Xray (обязателен).
- `XRAY_PORT` — порт Xray (по умолчанию `443`).
- `XRAY_FLOW` — поток (по умолчанию `xtls-rprx-vision`).

## Эндпоинты
Все вызовы (кроме `/healthz`) требуют заголовка `Authorization: Bearer $SUBS_INTERNAL_TOKEN`.

```bash
# assign
curl -s -X POST http://subs.securelink.svc.cluster.local:8080/v1/assign \
  -H "Authorization: Bearer $SUBS_INTERNAL_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"login":"user_login_or_email"}'

# revoke
curl -s -X POST http://subs.securelink.svc.cluster.local:8080/v1/revoke \
  -H "Authorization: Bearer $SUBS_INTERNAL_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"login":"user_login_or_email"}'

# status by login
curl -s -H "Authorization: Bearer $SUBS_INTERNAL_TOKEN" \
  'http://subs.securelink.svc.cluster.local:8080/v1/status?login=user@example.com'

# status by uid
curl -s -H "Authorization: Bearer $SUBS_INTERNAL_TOKEN" \
  'http://subs.securelink.svc.cluster.local:8080/v1/status?uid=<uuid>'

# VLESS ссылка
curl -s -H "Authorization: Bearer $SUBS_INTERNAL_TOKEN" \
  'http://subs.securelink.svc.cluster.local:8080/v1/sub?login=user@example.com&fmt=plain'
```

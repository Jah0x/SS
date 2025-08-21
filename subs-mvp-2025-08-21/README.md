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

## Эндпоинты
```bash
# assign
curl -s -X POST http://subs.securelink.svc.cluster.local:8080/v1/assign   -H "X-Internal-Token: $SUBS_INTERNAL_TOKEN"   -H 'Content-Type: application/json'   -d '{"login":"user_login_or_email"}'

# revoke
curl -s -X POST http://subs.securelink.svc.cluster.local:8080/v1/revoke   -H "X-Internal-Token: $SUBS_INTERNAL_TOKEN"   -H 'Content-Type: application/json'   -d '{"login":"user_login_or_email"}'

# uid status
curl -s -H "X-Internal-Token: $SUBS_INTERNAL_TOKEN"   http://subs.securelink.svc.cluster.local:8080/v1/uid/<uuid>
```

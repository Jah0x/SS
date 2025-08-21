# Subs DB Kit (Postgres)

Готовые миграции под **Postgres** и скрипт для применения в Kubernetes.

## Состав
- `migrations/20250818_subs_init.sql` — пулы, UID'ы, история назначений, состояние синка, функция `subs_assign_uid(...)`.
- `migrations/20250818_subs_login_patch.sql` — источники UID (из какого ConfigMap), резолвинг по логину (`subs_assign_uid_by_login`, `subs_revoke_by_login`).
- `scripts/apply_migrations_k8s.sh` — применяет обе миграции в Pod Postgres.

## Применение
```bash
# По умолчанию:
# NS=securelink, DB_USER=securelink, DB_NAME=securelink, PG_LABEL='app=postgres'

bash scripts/apply_migrations_k8s.sh

# Либо с переопределением:
NS=my-namespace DB_USER=myuser DB_NAME=mydb PG_LABEL='app=postgresql' bash scripts/apply_migrations_k8s.sh
```

## Быстрые проверки
```sql
-- Активный пул
SELECT * FROM pools;

-- Проверка колич. UID после наполнения watcher'ом
SELECT count(*) FROM uids;

-- Выдать UID по логину
SELECT subs_assign_uid_by_login('user_login_or_email');

-- Отозвать по логину
SELECT subs_revoke_by_login('user_login_or_email');
```

## Примечания
- Миграции идемпотентны, повторный запуск безопасен.
- Совместимо с Postgres 13+.

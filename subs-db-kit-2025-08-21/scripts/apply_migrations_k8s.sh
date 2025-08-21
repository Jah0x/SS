#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-securelink}"
DB_USER="${DB_USER:-securelink}"
DB_NAME="${DB_NAME:-securelink}"
PG_LABEL="${PG_LABEL:-app=postgres}"

echo "[i] Namespace: $NS"
echo "[i] DB user : $DB_USER"
echo "[i] DB name : $DB_NAME"
echo "[i] Label   : $PG_LABEL"

PG_POD="$(kubectl -n "$NS" get pod -l "$PG_LABEL" -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${PG_POD}" ]]; then
  echo "[!] Postgres pod not found by label: $PG_LABEL" >&2
  exit 1
fi
echo "[i] Using Postgres pod: $PG_POD"

for f in 20250818_subs_init.sql 20250818_subs_login_patch.sql; do
  echo "[i] Applying migration: $f"
  kubectl -n "$NS" cp "$(dirname "$0")/../migrations/$f" "$PG_POD:/tmp/$f"
  kubectl -n "$NS" exec -it "$PG_POD" -- bash -lc "psql -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1 -f /tmp/$f"
done

echo "[✓] Migrations applied successfully."

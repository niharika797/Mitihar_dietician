#!/usr/bin/env bash
# Restore the 30-day rig DB from the clean dump, apply the rig content patch, ANALYZE, restart API.
# Usage: reset_db.sh <perf.env> <dump>   (env PERF_DB_HOST / PERF_DB_NAME honoured for the API restart)
set -e
export MSYS_NO_PATHCONV=1
ENVF="$1"; DUMP="$2"; RIG="$(cd "$(dirname "$0")" && pwd -W)"
DC="docker compose -p mitihar-perf --env-file $ENVF -f $RIG/docker-compose.perf.yml"
$DC stop api >/dev/null 2>&1
docker exec mitihar-perf-pg psql -q -U admin -d postgres -c "DROP DATABASE IF EXISTS mityahar_db WITH (FORCE)" -c "CREATE DATABASE mityahar_db"
docker exec -i mitihar-perf-pg pg_restore -U admin -d mityahar_db --no-owner < "$DUMP"
docker exec mitihar-perf-pg psql -q -U admin -d mityahar_db -c "UPDATE recommendations SET created_at = week_start_date::timestamptz + interval '1 hour' WHERE NOT is_active" >/dev/null
# skip when the dump already carries the patch (dumps taken after patching, e.g. the 2 vCPU DB rebuild)
if [ "$(docker exec mitihar-perf-pg psql -U admin -d mityahar_db -t -A -c "select count(*) from food_items where source='rig_patch'")" = "0" ]; then
docker exec -i mitihar-perf-pg psql -q -U admin -d mityahar_db -v ON_ERROR_STOP=1 < "$RIG/content_patch_accomp.sql" >/dev/null
fi
# PERF_WEIGHT_AGED=1: patients signed up 40 days ago with no weight on record, so the 28-day weight rule lets one log through (row counts unchanged)
if [ "$PERF_WEIGHT_AGED" = "1" ]; then
docker exec mitihar-perf-pg psql -q -U admin -d mityahar_db -c "UPDATE patients SET created_at = created_at - interval '40 days'" -c "UPDATE progress_logs SET weight_kg = NULL"
fi
docker exec mitihar-perf-pg psql -q -U admin -d mityahar_db -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements" -c "ANALYZE" >/dev/null
$DC up -d --no-deps --force-recreate api >/dev/null 2>&1
C:/Users/Lenovo/perf-venv/Scripts/python.exe "$RIG/wait_ready.py" >/dev/null
echo "reset ok (db=${PERF_DB_NAME:-mityahar_db}, host=${PERF_DB_HOST:-pg})"

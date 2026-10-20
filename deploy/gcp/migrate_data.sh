#!/usr/bin/env bash
# Copy Railway's Postgres and document bucket into Google Cloud. Read-only on Railway, so it is safe to rehearse any number of times.
# For the real cut-over run it again after Railway has been stopped (see GOOGLE_CLOUD.md), with FINAL=1.
#   export RAILWAY_DATABASE_URL='postgresql://...'          # Railway → Postgres → Connect → public URL
#   export RAILWAY_S3_ENDPOINT=... RAILWAY_S3_BUCKET=... RAILWAY_S3_ACCESS_KEY=... RAILWAY_S3_SECRET_KEY=...
#   ./migrate_data.sh
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh
: "${RAILWAY_DATABASE_URL:?}" "${RAILWAY_S3_ENDPOINT:?}" "${RAILWAY_S3_BUCKET:?}" "${RAILWAY_S3_ACCESS_KEY:?}" "${RAILWAY_S3_SECRET_KEY:?}"
command -v pg_dump >/dev/null || { echo "install postgresql-client (pg_dump/pg_restore, version 16)"; exit 1; }
command -v rclone >/dev/null || { echo "install rclone"; exit 1; }
command -v cloud-sql-proxy >/dev/null || { echo "install cloud-sql-proxy: https://cloud.google.com/sql/docs/postgres/sql-proxy"; exit 1; }
CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
PASS=$(cat .dbpass 2>/dev/null || true); [ -n "$PASS" ] || read -r -s -p "Cloud SQL password for $DB_USER: " PASS
D=$(mktemp -d); trap 'kill ${PROXY:-0} 2>/dev/null || true; rm -rf "$D"' EXIT

echo "== 1/3 dump Railway Postgres"
pg_dump --no-owner --no-acl --format=custom --file="$D/tht.dump" "$RAILWAY_DATABASE_URL"
ls -lh "$D/tht.dump"

echo "== 2/3 restore into Cloud SQL (through the proxy)"
cloud-sql-proxy --port 5433 "$CONN" >"$D/proxy.log" 2>&1 & PROXY=$!
for i in $(seq 1 20); do (echo > /dev/tcp/127.0.0.1/5433) 2>/dev/null && break; sleep 1; done
export PGPASSWORD="$PASS"
# a rehearsal replaces the previous rehearsal: drop and recreate the public schema first
psql -h 127.0.0.1 -p 5433 -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
pg_restore --no-owner --no-acl --exit-on-error -h 127.0.0.1 -p 5433 -U "$DB_USER" -d "$DB_NAME" "$D/tht.dump"
psql -h 127.0.0.1 -p 5433 -U "$DB_USER" -d "$DB_NAME" -Atc "select 'households', count(*) from households union all select 'users', count(*) from users union all select 'household_state', count(*) from household_state"

echo "== 3/3 copy documents (Railway bucket → gs://$BUCKET)"
export RCLONE_CONFIG_RAIL_TYPE=s3 RCLONE_CONFIG_RAIL_PROVIDER=Other RCLONE_CONFIG_RAIL_ENDPOINT="$RAILWAY_S3_ENDPOINT" \
  RCLONE_CONFIG_RAIL_ACCESS_KEY_ID="$RAILWAY_S3_ACCESS_KEY" RCLONE_CONFIG_RAIL_SECRET_ACCESS_KEY="$RAILWAY_S3_SECRET_KEY" RCLONE_CONFIG_RAIL_REGION=auto
# Google side uses your own login:  gcloud auth application-default login
export RCLONE_CONFIG_GCS_TYPE="google cloud storage" RCLONE_CONFIG_GCS_ENV_AUTH=true RCLONE_CONFIG_GCS_BUCKET_POLICY_ONLY=true RCLONE_CONFIG_GCS_LOCATION="$REGION"
rclone copy "RAIL:$RAILWAY_S3_BUCKET" "GCS:$BUCKET" --transfers 16 --checksum --progress
echo "Objects: railway=$(rclone size --json "RAIL:$RAILWAY_S3_BUCKET" | python3 -c 'import sys,json;print(json.load(sys.stdin)["count"])')  google=$(rclone size --json "GCS:$BUCKET" | python3 -c 'import sys,json;print(json.load(sys.stdin)["count"])')"
echo "Done. Nothing on Railway was changed."

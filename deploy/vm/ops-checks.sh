#!/usr/bin/env bash
# Two safety nets, from Cloud Shell. Each is safe to run again.
#
#   bash deploy/vm/ops-checks.sh alerts you@example.com   # email when urbanhealth.in stops answering (uptime check every 5 min)
#   bash deploy/vm/ops-checks.sh restore                  # prove the backups restore: clone to a scratch instance, count rows, delete it
#   bash deploy/vm/ops-checks.sh backups                  # list the last backups and whether point-in-time recovery is on
#
# Nothing here prints a secret or touches the live database. "restore" creates a temporary Cloud SQL instance for about
# 15 minutes (a few rupees) and deletes it at the end.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh
gcloud config set project "$PROJECT_ID" >/dev/null

backups() {
  echo "Point-in-time recovery: $(gcloud sql instances describe "$SQL_INSTANCE" --format='value(settings.backupConfiguration.pointInTimeRecoveryEnabled)')"
  echo "Kept: $(gcloud sql instances describe "$SQL_INSTANCE" --format='value(settings.backupConfiguration.backupRetentionSettings.retainedBackups)') daily backups"
  gcloud sql backups list --instance="$SQL_INSTANCE" --limit=5 --format='table(windowStartTime.date("%d %b %Y %H:%M"),status,type)'
}

restore() {
  local tmp="uh-restore-drill-$(date +%m%d%H%M)"
  echo "Cloning $SQL_INSTANCE as it was 10 minutes ago into $tmp (takes ~10 min)…"
  gcloud sql instances clone "$SQL_INSTANCE" "$tmp" --point-in-time="$(date -u -d '-10 min' +%Y-%m-%dT%H:%M:%SZ)" --quiet
  trap 'echo "Deleting $tmp…"; gcloud sql instances delete "$tmp" --quiet' EXIT
  gcloud sql instances patch "$tmp" --no-deletion-protection --quiet >/dev/null 2>&1 || true
  echo "Clone is up. Row counts on the copy (the live database is not touched):"
  local pw; pw=$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')
  gcloud sql users set-password postgres --instance="$tmp" --password="$pw" --quiet >/dev/null
  PGPASSWORD="$pw" gcloud sql connect "$tmp" --user=postgres --database=tht --quiet <<'SQL'
select 'households' t, count(*) from households union all select 'people', count(*) from people
union all select 'health_records', count(*) from health_records union all select 'orders', count(*) from orders
union all select 'stored files', count(*) from files;
SQL
  echo "✓ Restore drill passed: backups can be brought back."
}

alerts() {
  local to="${1:?usage: ops-checks.sh alerts you@example.com}"
  local ch
  ch=$(gcloud beta monitoring channels list --filter="type=email AND labels.email_address=$to" --format='value(name)' | head -1)
  [[ -n "$ch" ]] || ch=$(gcloud beta monitoring channels create --type=email --display-name="Urban Health alerts" --channel-labels="email_address=$to" --format='value(name)')
  gcloud monitoring uptime list-configs --format='value(displayName)' | grep -qx "urbanhealth.in health" || \
    gcloud monitoring uptime create "urbanhealth.in health" --resource-type=uptime-url --resource-labels=host=urbanhealth.in,project_id="$PROJECT_ID" \
      --path=/api/health --protocol=https --period=5 --timeout=10 --matcher-content='"ok":true' --matcher-type=contains-string
  local pol=/tmp/uh-uptime-policy.json
  cat > "$pol" <<JSON
{"displayName": "urbanhealth.in is down",
 "combiner": "OR",
 "conditions": [{"displayName": "Health check failing from 2+ regions",
   "conditionThreshold": {"filter": "metric.type=\\"monitoring.googleapis.com/uptime_check/check_passed\\" AND resource.type=\\"uptime_url\\" AND metric.label.check_id=has_substring(\\"urbanhealth-in-health\\")",
     "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_NEXT_OLDER", "crossSeriesReducer": "REDUCE_COUNT_FALSE", "groupByFields": ["resource.label.host"]}],
     "comparison": "COMPARISON_GT", "thresholdValue": 1, "duration": "300s"}}],
 "notificationChannels": ["$ch"],
 "documentation": {"content": "urbanhealth.in/api/health has failed for 5+ minutes. Check the VM: gcloud compute ssh then sudo systemctl status urbanhealth.", "mimeType": "text/markdown"}}
JSON
  gcloud alpha monitoring policies list --format='value(displayName)' | grep -qx "urbanhealth.in is down" || gcloud alpha monitoring policies create --policy-from-file="$pol"
  echo "✓ $to gets an email if urbanhealth.in stops answering for 5 minutes."
}

case "${1:-}" in
  backups) backups ;; restore) restore ;; alerts) shift; alerts "$@" ;;
  *) echo "usage: $0 backups | restore | alerts you@example.com"; exit 2 ;;
esac

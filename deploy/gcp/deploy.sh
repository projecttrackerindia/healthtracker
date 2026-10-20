#!/usr/bin/env bash
# Build the image and deploy it to Cloud Run. Used by hand and by .github/workflows/gcp-deploy.yml.
#   ./deploy.sh                 # builds with Cloud Build
#   PREBUILT=1 ./deploy.sh      # image already pushed to $IMAGE (the GitHub workflow does this)
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh
gcloud config set project "$PROJECT_ID" >/dev/null
[ "${PREBUILT:-0}" = "1" ] || gcloud builds submit ../.. --tag "$IMAGE" --region "$REGION" --quiet
CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
SECRETS=$(grep -v '^\s*#' secrets.txt | grep -v '^\s*$' | while read -r n; do gcloud secrets describe "$n" >/dev/null 2>&1 && printf '%s=%s:latest,' "$n" "$n"; done | sed 's/,$//')

# min=max=1 instance, CPU always on, session affinity, 60-minute requests:
#  - video-call rooms and the daily jobs (medicine nudges, weekly report, housekeeping) live inside this one process
#  - WebSocket calls need requests that can last an hour
gcloud run deploy "$SERVICE" --image "$IMAGE" --region "$REGION" --service-account "$RUN_SA" --allow-unauthenticated \
  --port 8080 --cpu 1 --memory 1Gi --cpu-boost --no-cpu-throttling --min-instances 1 --max-instances 1 --concurrency 80 \
  --timeout 3600 --session-affinity --add-cloudsql-instances "$CONN" \
  --env-vars-file env.yaml --set-secrets "$SECRETS" --quiet
URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo "Deployed: $URL"
for i in 1 2 3 4 5 6; do curl -fsS "$URL/api/health" && echo && exit 0 || sleep 5; done
echo "Health check failed — gcloud run services logs read $SERVICE --region $REGION --limit 50"; exit 1

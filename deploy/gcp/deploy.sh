#!/usr/bin/env bash
# Build the image and deploy it to Cloud Run. Used by hand and by .github/workflows/gcp-deploy.yml.
#   ./deploy.sh                 # builds with Cloud Build
#   PREBUILT=1 ./deploy.sh      # image already pushed to $IMAGE (the GitHub workflow does this)
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh
gcloud config set project "$PROJECT_ID" >/dev/null
# Stamp the commit being deployed into env.yaml, so /api/health can answer "did that land?" from one public
# URL. It has reported "dev" since the move off Railway, which is how several deploys this week were
# verified by eye instead of by asking.
SHA=$(git -C ../.. rev-parse --short=10 HEAD 2>/dev/null || echo unknown)
./stamp-env.sh "$SHA"

echo "Deploying $SHA"
[ "${PREBUILT:-0}" = "1" ] || gcloud builds submit ../.. --tag "$IMAGE" --region "$REGION" --quiet
CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"

SECRETS=$(grep -v '^\s*#' secrets.txt | grep -v '^\s*$' | while read -r n; do gcloud secrets describe "$n" >/dev/null 2>&1 && printf '%s=%s:latest,' "$n" "$n" || true; done | sed 's/,$//')   # optional secrets may not exist yet; without `|| true` pipefail aborts the deploy

# min=max=1 instance, CPU always on, session affinity, 60-minute requests:
#  - video-call rooms and the daily jobs (medicine nudges, weekly report, housekeeping) live inside this one process
#  - WebSocket calls need requests that can last an hour
gcloud run deploy "$SERVICE" --image "$IMAGE" --region "$REGION" --service-account "$RUN_SA" --allow-unauthenticated \
  --port 8080 --cpu 1 --memory 1Gi --cpu-boost --no-cpu-throttling --min-instances 1 --max-instances 1 --concurrency 80 \
  --timeout 3600 --session-affinity --add-cloudsql-instances "$CONN" \
  --env-vars-file env.yaml --set-secrets "$SECRETS" --quiet
URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo "Deployed: $URL"

# Verify the commit, not just that something answers. The old loop accepted any 200 from /api/health, so a deploy
# that never ran still "passed" — the previous revision was alive and answering the whole time. Two deploys failed
# on an unselected gcloud account and were reported as successful for half an hour because of exactly this.
for i in $(seq 1 24); do
  LIVE=$(curl -fsS --max-time 10 "$URL/api/health" 2>/dev/null | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  [ "$LIVE" = "$SHA" ] && { echo "Verified: /api/health reports $LIVE"; exit 0; }
  [ -n "$LIVE" ] && echo "  serving $LIVE, waiting for $SHA ($i/24)" || echo "  no answer yet ($i/24)"
  sleep 5
done
echo "FAILED: $URL/api/health still does not report $SHA after two minutes."
echo "The service may be serving the previous revision. Check:"
echo "  gcloud run services logs read $SERVICE --region $REGION --limit 50"
exit 1

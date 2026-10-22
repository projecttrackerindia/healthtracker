#!/usr/bin/env bash
# Build the current commit and put it on the VM, in one command.
#
# This is what the GitHub workflow does; it exists for the window before Workload Identity is configured,
# and for the times Cloud Shell is the only way in. The long pasted pipeline it replaces was retyped by hand
# every release, which is both tedious and exactly how a wrong flag gets in unnoticed.
#
#   ./ship.sh
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

SHA=$(git -C ../.. rev-parse --short=10 HEAD)
TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/tht/tht:${SHA}"
echo "== Shipping $SHA"

# The Maps browser key lives outside the repo; pick it up if it is there, otherwise leave env.yaml alone.
[ -f ~/brw.key ] && export GOOGLE_MAPS_KEY="$(cat ~/brw.key)"
( cd ../gcp && ./stamp-env.sh "$SHA" )

echo "== Build"
gcloud builds submit ../.. --tag "$TAG" --region "$REGION" --quiet

echo "== Release"
gcloud compute scp --zone "$ZONE" --quiet ../gcp/env.yaml ../gcp/secrets.txt "$VM":/tmp/
gcloud compute ssh "$VM" --zone "$ZONE" --quiet --command "
  set -e
  sudo install -d -m 0755 /opt/urbanhealth/repo/deploy/gcp
  sudo install -m 0644 /tmp/env.yaml /tmp/secrets.txt /opt/urbanhealth/repo/deploy/gcp/
  sudo urbanhealth-release '$TAG' '$SHA'
"

echo "== Live"
curl -fsS "https://${CANONICAL_HOST:-urbanhealth.in}/api/health"; echo

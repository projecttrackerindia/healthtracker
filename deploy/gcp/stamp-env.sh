#!/usr/bin/env bash
# Write the deploy-time values into env.yaml: the commit, the build time, the real bucket, and the Maps
# browser key if the caller has one.
#
# Shared by the Cloud Run deploy and the VM release on purpose. The first version of the VM path did not
# stamp APP_VERSION at all, so /api/health reported "dev" and release.sh had nothing real to compare the
# commit against — a verification step that could only ever pass. Two copies of this logic is how that
# happens; one copy is the fix.
#
#   stamp-env.sh <sha>
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

SHA="${1:?usage: stamp-env.sh <sha>}"
STAMPS=("APP_VERSION:$SHA" "APP_BUILT:$(date -u +%Y-%m-%dT%H:%M:%SZ)" "S3_BUCKET:$BUCKET")
[ -n "${GOOGLE_MAPS_KEY:-}" ] && STAMPS+=("GOOGLE_MAPS_KEY:$GOOGLE_MAPS_KEY")

for k in "${STAMPS[@]}"; do
  n=${k%%:*}; v=${k#*:}
  if grep -q "^${n}:" env.yaml; then sed -i "s|^${n}:.*|${n}: \"${v}\"|" env.yaml
  else printf '%s: "%s"\n' "$n" "$v" >> env.yaml; fi
done
echo "stamped env.yaml: APP_VERSION=$SHA S3_BUCKET=$BUCKET"

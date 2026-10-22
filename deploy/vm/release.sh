#!/usr/bin/env bash
# Put a new build on the VM. Run over SSH by the GitHub workflow; safe to run by hand.
#   release.sh <image> <commit-sha>
set -euo pipefail
IMAGE="$1"; SHA="${2:-}"

sudo install -d -m 0755 /opt/urbanhealth/repo
# env.yaml and secrets.txt travel with the release, so the settings on the box always match the commit
# running on it. They are copied in by the caller before this script runs.
sudo sed -i "s|^IMAGE=.*|IMAGE=$IMAGE|" /etc/urbanhealth/release.env

sudo -E gcloud auth configure-docker "$(echo "$IMAGE" | cut -d/ -f1)" --quiet >/dev/null
sudo docker pull "$IMAGE"
sudo systemctl restart urbanhealth

# Verify the commit, not that something answers. The previous container keeps serving a perfectly good 200
# while a failed release does nothing at all, which is exactly how two Cloud Run deploys were reported as
# successful for half an hour.
for i in $(seq 1 24); do
  LIVE=$(curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null \
         | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  if [ -z "$SHA" ] && [ -n "$LIVE" ]; then echo "up: $LIVE"; exit 0; fi
  [ "$LIVE" = "$SHA" ] && { echo "verified: $LIVE"; exit 0; }
  [ -n "$LIVE" ] && echo "  serving $LIVE, waiting for $SHA ($i/24)" || echo "  no answer yet ($i/24)"
  sleep 5
done
echo "FAILED: the app does not report $SHA. journalctl -u urbanhealth -n 50"
sudo journalctl -u urbanhealth -n 30 --no-pager || true
exit 1

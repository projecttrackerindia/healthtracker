#!/usr/bin/env bash
# Put a new build on the VM. Run over SSH by the GitHub workflow; safe to run by hand.
#   release.sh <image> <commit-sha>
set -euo pipefail
IMAGE="$1"; SHA="${2:-}"

sudo install -d -m 0755 /opt/urbanhealth/repo
# env.yaml and secrets.txt travel with the release, so the settings on the box always match the commit
# running on it. They are copied in by the caller before this script runs.
sudo sed -i "s|^IMAGE=.*|IMAGE=$IMAGE|" /etc/urbanhealth/release.env

# Keep system and container logs for 400 days (CERT-In asks for 180), capped at 4 GB. Idempotent.
if [ ! -f /etc/systemd/journald.conf.d/urbanhealth.conf ]; then
  sudo install -d /etc/systemd/journald.conf.d
  printf '[Journal]\nStorage=persistent\nMaxRetentionSec=400day\nSystemMaxUse=4G\n' | sudo tee /etc/systemd/journald.conf.d/urbanhealth.conf >/dev/null
  sudo systemctl restart systemd-journald
fi
# Container output goes to the journal, so it is kept by the rule above.
if ! grep -q -- '--log-driver=journald' /etc/systemd/system/urbanhealth.service; then
  sudo sed -i 's|docker run --rm --name urbanhealth \\|docker run --rm --name urbanhealth --log-driver=journald \\|' /etc/systemd/system/urbanhealth.service
  sudo systemctl daemon-reload
fi
# Virus scanning of uploads (ClamAV). It needs ~1.5 GB of memory, more than an e2-small has spare, so it starts
# only when the machine is big enough: set CLAMAV=1 in /etc/urbanhealth/release.env after moving to e2-medium.
if grep -q '^CLAMAV=1' /etc/urbanhealth/release.env 2>/dev/null; then
  sudo docker network inspect uh >/dev/null 2>&1 || sudo docker network create uh >/dev/null
  if ! sudo docker ps --format '{{.Names}}' | grep -qx clamav; then
    sudo docker rm -f clamav >/dev/null 2>&1 || true
    sudo docker run -d --name clamav --restart unless-stopped --network uh --log-driver=journald clamav/clamav:stable >/dev/null
  fi
  grep -q -- '--network uh' /etc/systemd/system/urbanhealth.service || { sudo sed -i 's|docker run --rm --name urbanhealth |docker run --rm --name urbanhealth --network uh |' /etc/systemd/system/urbanhealth.service; sudo systemctl daemon-reload; }
fi

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

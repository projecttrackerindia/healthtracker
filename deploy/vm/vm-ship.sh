#!/usr/bin/env bash
# Deploy without Cloud Shell: run this ON the VM, from the "SSH" button on the VM in the Google Cloud Console.
#
#   curl -fsSL https://raw.githubusercontent.com/projecttrackerindia/healthtracker/main/deploy/vm/vm-ship.sh | bash
#
# It downloads the latest commit of main from GitHub (the repo is public, so no credentials are needed), builds
# the image on this machine, points the service at it, restarts and checks /api/health reports the new commit.
# The settings already on the box (env.yaml and secrets in Secret Manager) are kept; only the version is stamped.
# If the new build fails to come up, the previous image is put back.
set -euo pipefail
REPO="projecttrackerindia/healthtracker"
REF="${1:-main}"

SHA=$(curl -fsS "https://api.github.com/repos/$REPO/commits/$REF" | sed -n 's/^  "sha": "\([0-9a-f]\{10\}\).*/\1/p' | head -1)
[ -n "$SHA" ] || { echo "Could not read the latest commit from GitHub"; exit 1; }
echo "== Shipping $SHA"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$SHA" | tar xz -C "$WORK" --strip-components=1

echo "== Build (a few minutes on this machine)"
sudo docker build -q -t "urbanhealth-local:$SHA" "$WORK" >/dev/null
echo "built urbanhealth-local:$SHA"

echo "== Release"
SRC=/opt/urbanhealth/repo/deploy/gcp
ENVY="$SRC/env.yaml"
sudo install -d -m 0755 "$SRC"
for kv in "APP_VERSION:$SHA" "APP_BUILT:$(date -u +%Y-%m-%dT%H:%M:%SZ)"; do
  n=${kv%%:*}; v=${kv#*:}
  if sudo grep -q "^${n}:" "$ENVY"; then sudo sed -i "s|^${n}:.*|${n}: \"${v}\"|" "$ENVY"
  else echo "${n}: \"${v}\"" | sudo tee -a "$ENVY" >/dev/null; fi
done
# new secret names the code expects; the values stay in Secret Manager
sudo install -m 0644 "$WORK/deploy/gcp/secrets.txt" "$SRC/secrets.txt" 2>/dev/null || true
sudo install -m 0755 "$WORK/deploy/vm/urbanhealth-env" /usr/local/bin/urbanhealth-env
sudo install -m 0755 "$WORK/deploy/vm/release.sh" /usr/local/bin/urbanhealth-release

PREV=$(sudo sed -n 's/^IMAGE=//p' /etc/urbanhealth/release.env)
sudo sed -i "s|^IMAGE=.*|IMAGE=urbanhealth-local:$SHA|" /etc/urbanhealth/release.env
sudo systemctl restart urbanhealth

for i in $(seq 1 30); do
  LIVE=$( (curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null || true) | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  if [ "$LIVE" = "$SHA" ]; then
    echo "== Live and verified: $SHA"
    sudo docker image prune -f >/dev/null 2>&1 || true
    exit 0
  fi
  echo "  waiting ($i/30)${LIVE:+, serving $LIVE}"
  sleep 5
done

echo "FAILED to start $SHA — putting back $PREV"
sudo journalctl -u urbanhealth -n 30 --no-pager || true
sudo sed -i "s|^IMAGE=.*|IMAGE=$PREV|" /etc/urbanhealth/release.env
sudo systemctl restart urbanhealth
exit 1

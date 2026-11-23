#!/usr/bin/env bash
# Ship a patch on top of the image that is running now, without a full rebuild. Run this ON the VM, from the
# "SSH" button on the VM in the Google Cloud Console:
#
#   curl -fsSL https://raw.githubusercontent.com/projecttrackerindia/healthtracker/<commit>/deploy/vm/vm-patch.sh | bash -s <commit> <tag>
#
# deploy/vm/patches/<tag>.txt (in that commit) lists what changes: "+ path" is copied in from the commit,
# "- path" is deleted from the image. The new image is the running one plus those files, tagged
# urbanhealth-local:<tag>. The service is pointed at it and restarted; /api/health must then report the
# service-worker version of the commit and the first new asset must be served. If not, the previous image is put
# back. Settings and secrets on the box are not touched.
set -euo pipefail
REPO="projecttrackerindia/healthtracker"
SHA="${1:?commit}"; TAG="${2:?tag, e.g. hbag40}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/src" "$WORK/ctx/files"

echo "== Download $SHA"
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$SHA" \
  | tar xz -C "$WORK/src" --strip-components=1 --wildcards --no-wildcards-match-slash \
      'healthtracker-*/web' 'healthtracker-*/api' 'healthtracker-*/admin' 'healthtracker-*/partner' 'healthtracker-*/tech' \
      'healthtracker-*/site' 'healthtracker-*/server.py' 'healthtracker-*/deploy/vm'
LIST="$WORK/src/deploy/vm/patches/$TAG.txt"
[ -f "$LIST" ] || { echo "No list for $TAG in $SHA"; exit 1; }

: > "$WORK/ctx/remove.txt"
ADD=0; DEL=0; PROBE=""
while read -r op path || [ -n "${op:-}" ]; do
  case "$op" in
    +) [ -f "$WORK/src/$path" ] || { echo "Missing in the commit: $path"; exit 1; }
       install -D -m 0644 "$WORK/src/$path" "$WORK/ctx/files/$path"; ADD=$((ADD+1))
       case "$path" in web/a/*) [ -z "$PROBE" ] && PROBE="/a/${path#web/a/}";; esac ;;
    -) echo "$path" >> "$WORK/ctx/remove.txt"; DEL=$((DEL+1)) ;;
    ''|'#'*) ;;
    *) echo "Bad line: $op $path"; exit 1 ;;
  esac
done < "$LIST"
echo "   $ADD files in, $DEL out"

cat > "$WORK/ctx/Dockerfile" <<'EOF'
ARG BASE
FROM ${BASE}
USER root
COPY files/ /app/
COPY remove.txt /tmp/remove.txt
RUN cd /app && xargs -r rm -f < /tmp/remove.txt && rm -f /tmp/remove.txt
USER tht
EOF

PREV=$(sudo sed -n 's/^IMAGE=//p' /etc/urbanhealth/release.env)
[ -n "$PREV" ] || { echo "Could not read the running image"; exit 1; }
echo "== Build urbanhealth-local:$TAG on $PREV"
sudo docker build -q --build-arg BASE="$PREV" -t "urbanhealth-local:$TAG" "$WORK/ctx" >/dev/null

WANT=$(sed -n "s/^const V='\([^']*\)'.*/\1/p" "$WORK/src/web/sw.js" | head -1)
echo "== Release (expecting sw $WANT)"
sudo sed -i "s|^IMAGE=.*|IMAGE=urbanhealth-local:$TAG|" /etc/urbanhealth/release.env
sudo systemctl restart urbanhealth

for i in $(seq 1 30); do
  SW=$( (curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null || true) | sed -n 's/.*"sw"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  if [ "$SW" = "$WANT" ]; then
    CODE=200
    [ -n "$PROBE" ] && CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:8080$PROBE" || true)
    if [ "$CODE" = "200" ]; then
      echo "== Live and verified: urbanhealth-local:$TAG (sw $SW${PROBE:+, $PROBE served})"
      echo "   previous image kept for rollback: $PREV"
      exit 0
    fi
    echo "  new version up but $PROBE answered $CODE"
    break
  fi
  echo "  waiting ($i/30)${SW:+, serving $SW}"
  sleep 5
done

echo "FAILED to start urbanhealth-local:$TAG — putting back $PREV"
sudo journalctl -u urbanhealth -n 30 --no-pager || true
sudo sed -i "s|^IMAGE=.*|IMAGE=$PREV|" /etc/urbanhealth/release.env
sudo systemctl restart urbanhealth
exit 1

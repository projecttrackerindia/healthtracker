#!/usr/bin/env bash
# Put the launch keys into Secret Manager and restart the app, from Cloud Shell. Safe to run again.
#
#   bash deploy/vm/set-keys.sh                 # checks every key and asks only for what is missing
#   bash deploy/vm/set-keys.sh vapid           # phone notifications (generated here, nothing to paste)
#   bash deploy/vm/set-keys.sh maps            # Google Maps browser key (live tracking, SOS map)
#   bash deploy/vm/set-keys.sh firebase        # mobile number sign-in codes via Firebase
#   bash deploy/vm/set-keys.sh datakey         # checks DATA_KEY exists; creates it only if it never existed
#
# Keys are never printed, never written to the repo, and never sent anywhere but Secret Manager.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh
gcloud config set project "$PROJECT_ID" >/dev/null

has()  { gcloud secrets versions access latest --secret="$1" >/dev/null 2>&1; }
put()  {   # put NAME VALUE
  gcloud secrets describe "$1" >/dev/null 2>&1 || gcloud secrets create "$1" --replication-policy=automatic >/dev/null
  printf '%s' "$2" | gcloud secrets versions add "$1" --data-file=- >/dev/null
  gcloud secrets add-iam-policy-binding "$1" --member="serviceAccount:$VM_SA" --role=roles/secretmanager.secretAccessor >/dev/null 2>&1 || true
  echo "  ✓ $1 saved"
}
ask()  { local v; read -r -s -p "  $1: " v; echo; printf '%s' "$v"; }
CHANGED=0

vapid() {
  echo "Phone notifications (Web Push)"
  if has VAPID_PRIVATE_KEY; then echo "  ✓ VAPID_PRIVATE_KEY already set — keeping it (changing it would silence every phone already subscribed)"; return; fi
  python3 -c "import cryptography" 2>/dev/null || pip3 install --quiet --user cryptography
  key=$(python3 - <<'PY'
import base64
from cryptography.hazmat.primitives.asymmetric import ec
k = ec.generate_private_key(ec.SECP256R1())
print(base64.urlsafe_b64encode(k.private_numbers().private_value.to_bytes(32, "big")).decode().rstrip("="))
PY
)
  put VAPID_PRIVATE_KEY "$key"
  has VAPID_SUBJECT || put VAPID_SUBJECT "mailto:support@urbanhealth.in"
  CHANGED=1
}

maps() {
  echo "Google Maps (browser key)"
  echo "  Create it in Console → Google Maps Platform → Keys. Enable Maps JavaScript API."
  echo "  Restrict it: Application = Websites, https://urbanhealth.in/* and https://www.urbanhealth.in/*"
  if has GOOGLE_MAPS_KEY; then read -r -p "  GOOGLE_MAPS_KEY is set. Replace it? [y/N] " a; [[ "$a" == [yY] ]] || return; fi
  v=$(ask "Paste the key (hidden)"); [[ -n "$v" ]] || { echo "  skipped"; return; }
  [[ "$v" == AIza* ]] || { echo "  that does not look like a Google API key (starts with AIza) — skipped"; return; }
  put GOOGLE_MAPS_KEY "$v"; CHANGED=1
}

firebase() {
  echo "Mobile sign-in codes (Firebase Phone Authentication, project ${FIREBASE_PROJECT:-central-weft-511003-c1-a16ed})"
  echo "  Firebase console → Project settings → Your apps → Web app config. Also: Authentication → Sign-in method → Phone = on,"
  echo "  and Authentication → Settings → Authorized domains: urbanhealth.in"
  for n in FIREBASE_WEB_API_KEY FIREBASE_PROJECT_ID FIREBASE_APP_ID; do
    if has "$n"; then echo "  ✓ $n already set"; continue; fi
    v=$(ask "$n"); [[ -n "$v" ]] && { put "$n" "$v"; CHANGED=1; } || echo "  skipped $n"
  done
  echo "  (Firebase becomes the SMS channel automatically once FIREBASE_WEB_API_KEY is set, unless MSG91 keys are added later.)"
}

datakey() {
  echo "Health data encryption key"
  if has DATA_KEY; then echo "  ✓ DATA_KEY is set. Never change it: records encrypted with it could not be read again."; return; fi
  echo "  DATA_KEY is NOT set. The app is encrypting with a key derived from SECRET_KEY."
  echo "  If families already have data, do not add DATA_KEY now — ask before changing encryption on live data."
  read -r -p "  Is the database still empty of real families? Create DATA_KEY now? [y/N] " a
  [[ "$a" == [yY] ]] || return
  put DATA_KEY "$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"; CHANGED=1
}

case "${1:-all}" in
  vapid) vapid ;; maps) maps ;; firebase) firebase ;; datakey) datakey ;;
  all) datakey; vapid; maps; firebase ;;
  *) echo "usage: $0 [vapid|maps|firebase|datakey]"; exit 2 ;;
esac

if [[ "$CHANGED" == 1 ]]; then
  echo "Restarting the app on $VM so it picks the keys up…"
  gcloud compute ssh "$VM" --zone "$ZONE" --quiet --command "sudo systemctl restart urbanhealth" && echo "  ✓ restarted"
  echo "Check: curl -s https://urbanhealth.in/api/v1/config | grep -o '\"maps\":{[^}]*' ; and Settings → Notifications in the app."
else
  echo "Nothing changed."
fi

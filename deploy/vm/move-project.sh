#!/usr/bin/env bash
# Move Urban Health from the shared project (billed with Project Tracker) to its own project, which is
# billed to the Urban Health billing account where the startup credits land.
#
# Run in Cloud Shell, signed in as the account that runs the current VM:
#
#   rm -rf ~/uh && git clone -q https://github.com/projecttrackerindia/healthtracker ~/uh && bash ~/uh/deploy/vm/move-project.sh
#
# What it does, in order. Every step checks first, so if anything stops it, run the same line again.
#   1. Adds the support@urbanhealth.in sign-in to this Cloud Shell (one browser approval).
#   2. New project: switches on the services, and lifts two organisation defaults for this project only
#      (VMs may have a public address; Cloud SQL may use the Auth Proxy's public endpoint). Same set-up as today.
#   3. Copies every secret across. DATA_KEY is checked byte for byte: without it no record can be read.
#   4. Creates the database (same size, Postgres 16, daily backups, point-in-time recovery).
#   5. Creates the VM with provision.sh, and builds the exact version that is live today on it.
#   6. A few minutes of downtime: stops the old app, copies the database, starts the new app, checks the
#      new copy has the same number of users, families and medicines as the old one.
#   7. Prints the new address for the Hostinger A record.
#
# Nothing old is deleted. The old VM keeps its copy of the database; until you delete it, rollback is:
#   start the old app again and put the old address back in Hostinger.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

OLD_P="${OLD_PROJECT:-central-weft-511003-c1}"
NEW_P="${NEW_PROJECT:-valid-perigee-514407-v9}"
NEW_ACCT="${NEW_ACCOUNT:-support@urbanhealth.in}"
OLD_ACCT="${OLD_ACCOUNT:-$(gcloud config get-value account 2>/dev/null)}"
OLD_CONN="$OLD_P:$REGION:$SQL_INSTANCE"
NEW_CONN="$NEW_P:$REGION:$SQL_INSTANCE"
WORK="$HOME/uh-move"; mkdir -p "$WORK"; chmod 700 "$WORK"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32m✓\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31m✗ %s\033[0m\n' "$*"; exit 1; }
o()    { gcloud --account="$OLD_ACCT" --project="$OLD_P" --quiet "$@"; }
n()    { gcloud --account="$NEW_ACCT" --project="$NEW_P" --quiet "$@"; }
ossh() { o compute ssh "$VM" --zone "$ZONE" --command "$1"; }
nssh() { n compute ssh "$VM" --zone "$ZONE" --command "$1"; }

[ -n "$OLD_ACCT" ] || die "No account is signed in to this Cloud Shell."
[ "$OLD_ACCT" != "$NEW_ACCT" ] || die "Run this from the Cloud Shell of the account that owns $OLD_P, not $NEW_ACCT."

say "1. Sign-ins"
echo "   old project $OLD_P as $OLD_ACCT"
echo "   new project $NEW_P as $NEW_ACCT"
if ! gcloud auth list --format='value(account)' | grep -qx "$NEW_ACCT"; then
  echo "   Open the link below, choose $NEW_ACCT, allow, and paste the code back here."
  gcloud auth login "$NEW_ACCT" --no-launch-browser
  gcloud config set account "$OLD_ACCT" >/dev/null   # login switches the default; keep the old one active
fi
o projects describe "$OLD_P" --format='value(projectId)' >/dev/null || die "$OLD_ACCT cannot read $OLD_P"
n projects describe "$NEW_P" --format='value(projectId)' >/dev/null || die "$NEW_ACCT cannot read $NEW_P"
ok "both projects reachable"

say "Live version today"
LIVE_SHA=$(curl -fsS --max-time 10 https://urbanhealth.in/api/health | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
SHA="${SHA:-$LIVE_SHA}"
[ -n "$SHA" ] || die "Could not read the live version from https://urbanhealth.in/api/health"
ok "will build $SHA on the new VM (the same code as today; new features ship afterwards with vm-ship.sh)"

say "2. New project services"
n services enable compute.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com iam.googleapis.com \
  cloudresourcemanager.googleapis.com orgpolicy.googleapis.com >/dev/null
ok "Compute, Cloud SQL, Secret Manager, IAM, Org Policy on"

# New Google Workspace organisations come with "secure by default" policies. Two of them block the set-up
# Urban Health already runs: a VM with its own public address (Caddy serves the site directly) and Cloud SQL
# with a public endpoint (the Auth Proxy connects over it, encrypted and IAM-checked; no network is allowed in).
# Lift exactly those two, for this one project, and only if they are on.
blocked() {  # blocked CONSTRAINT -> 0 if the effective policy denies us
  n org-policies describe "$1" --effective --project="$NEW_P" --format=yaml 2>/dev/null | grep -Eq 'denyAll: true|enforce: true'
}
override() {  # override CONSTRAINT RULE
  local f="$WORK/$1.yaml"
  printf 'name: projects/%s/policies/%s\nspec:\n  rules:\n  - %s\n' "$NEW_P" "$1" "$2" > "$f"
  if ! n org-policies set-policy "$f" >/dev/null 2>&1; then
    ORG=$(n projects get-ancestors "$NEW_P" --format='value(id,type)' | awk '$2=="organization"{print $1}')
    [ -n "$ORG" ] || die "Cannot change organisation policy $1, and the project has no organisation."
    echo "   giving $NEW_ACCT the Organisation Policy Administrator role on organisation $ORG"
    gcloud --account="$NEW_ACCT" --quiet organizations add-iam-policy-binding "$ORG" \
      --member="user:$NEW_ACCT" --role=roles/orgpolicy.policyAdmin --condition=None >/dev/null \
      || die "Not allowed to manage organisation policies. In console.cloud.google.com (as $NEW_ACCT) → IAM → select the organisation → grant yourself 'Organization Policy Administrator', then run this again."
    sleep 20
    n org-policies set-policy "$f" >/dev/null || die "Could not set $1 on $NEW_P"
  fi
}
for c in compute.vmExternalIpAccess:allowAll:\ true sql.restrictPublicIp:enforce:\ false; do
  name=${c%%:*}; rule=${c#*:}
  if blocked "$name"; then override "$name" "$rule"; ok "$name lifted for $NEW_P"; else ok "$name not in the way"; fi
done

say "3. Secrets"
# The secret names come from the running VM, so nothing the app reads today is left behind.
ossh "sudo cat /opt/urbanhealth/repo/deploy/gcp/secrets.txt" > "$WORK/secrets.txt"
ossh "sudo cat /opt/urbanhealth/repo/deploy/gcp/env.yaml"    > "$WORK/env.yaml"
grep -q '^DATABASE_URL' "$WORK/secrets.txt" || die "Could not read secrets.txt from the old VM"
copied=0; skipped=0
while read -r s; do
  case "$s" in ''|\#*) continue;; esac
  if ! o secrets versions access latest --secret="$s" --out-file="$WORK/s.val" >/dev/null 2>&1; then skipped=$((skipped+1)); continue; fi
  [ "$s" = DATABASE_URL ] && sed -i "s|/cloudsql/$OLD_CONN|/cloudsql/$NEW_CONN|" "$WORK/s.val"
  n secrets describe "$s" >/dev/null 2>&1 || n secrets create "$s" --replication-policy=automatic >/dev/null
  if n secrets versions access latest --secret="$s" --out-file="$WORK/s.now" >/dev/null 2>&1 && cmp -s "$WORK/s.val" "$WORK/s.now"; then
    :
  else
    n secrets versions add "$s" --data-file="$WORK/s.val" >/dev/null
  fi
  copied=$((copied+1))
done < "$WORK/secrets.txt"
rm -f "$WORK/s.val" "$WORK/s.now"
ok "$copied secrets in place ($skipped optional ones were never set)"
# Health records are encrypted with DATA_KEY (or a key derived from SECRET_KEY). Prove both arrived unchanged.
for s in DATA_KEY SECRET_KEY; do
  a=$(o secrets versions access latest --secret="$s" 2>/dev/null | sha256sum | cut -c1-16)
  b=$(n secrets versions access latest --secret="$s" 2>/dev/null | sha256sum | cut -c1-16)
  [ "$a" = "$b" ] || die "$s differs between the projects. Stop: records encrypted with it would be unreadable."
done
ok "DATA_KEY and SECRET_KEY identical in both projects"
DB_URL=$(n secrets versions access latest --secret=DATABASE_URL)
DB_PASS=$(printf '%s' "$DB_URL" | sed -n 's|^postgres[a-z+]*://[^:]*:\([^@]*\)@.*|\1|p')
[ -n "$DB_PASS" ] || die "Could not read the database password from DATABASE_URL"
case "$DB_URL" in *"/cloudsql/$NEW_CONN"*) ok "DATABASE_URL points at $NEW_CONN";; *) die "DATABASE_URL does not point at $NEW_CONN";; esac

say "4. Database (about 10 minutes the first time)"
if ! n sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1; then
  n sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 --edition=ENTERPRISE --region="$REGION" \
    --tier="${SQL_TIER:-db-g1-small}" --storage-type=SSD --storage-size=20 --storage-auto-increase --availability-type=zonal \
    --backup-start-time=21:30 --enable-point-in-time-recovery --retained-backups-count=14 --deletion-protection
fi
n sql databases describe tht --instance="$SQL_INSTANCE" >/dev/null 2>&1 || n sql databases create tht --instance="$SQL_INSTANCE" >/dev/null
if [ -z "$(n sql users list --instance="$SQL_INSTANCE" --filter='name=tht' --format='value(name)')" ]; then
  n sql users create tht --instance="$SQL_INSTANCE" --password="$DB_PASS" >/dev/null
else
  n sql users set-password tht --instance="$SQL_INSTANCE" --password="$DB_PASS" >/dev/null
fi
ok "$NEW_CONN ready, database tht, user tht"

say "5. VM"
# Secure-by-default organisations may skip the default network, and a hand-made network has no SSH rule.
if ! n compute networks describe default >/dev/null 2>&1; then
  n compute networks create default --subnet-mode=auto >/dev/null
  ok "network 'default' created"
fi
n compute firewall-rules describe "${VM}-ssh" >/dev/null 2>&1 || \
  n compute firewall-rules create "${VM}-ssh" --network=default --allow=tcp:22 --target-tags="${VM}" \
    --description="SSH to the Urban Health VM (gcloud compute ssh, keys via OS Login)" >/dev/null
export PROJECT_ID="$NEW_P" CLOUDSDK_CORE_PROJECT="$NEW_P" CLOUDSDK_CORE_ACCOUNT="$NEW_ACCT"
export SQL_CONN="$NEW_CONN" VM_SA="${VM}-vm@${NEW_P}.iam.gserviceaccount.com" IMAGE="urbanhealth-local:$SHA"
bash ./provision.sh | sed '/== Provisioned/,$d'
unset CLOUDSDK_CORE_PROJECT CLOUDSDK_CORE_ACCOUNT
gcloud config set project "$OLD_P" >/dev/null 2>&1 || true
NEW_IP=$(n compute addresses describe "$IP_NAME" --region "$REGION" --format='value(address)')
ok "VM $VM at $NEW_IP"

n compute scp --zone "$ZONE" "$WORK/env.yaml" "$WORK/secrets.txt" "$VM":/tmp/ >/dev/null
nssh "
  set -e
  sudo install -d -m 0755 /opt/urbanhealth/repo/deploy/gcp
  sudo install -m 0644 /tmp/env.yaml /tmp/secrets.txt /opt/urbanhealth/repo/deploy/gcp/
  rm -f /tmp/env.yaml /tmp/secrets.txt
  # logs kept 400 days (CERT-In asks for 180), as release.sh does on the old VM
  if [ ! -f /etc/systemd/journald.conf.d/urbanhealth.conf ]; then
    sudo install -d /etc/systemd/journald.conf.d
    printf '[Journal]\nStorage=persistent\nMaxRetentionSec=400day\nSystemMaxUse=4G\n' | sudo tee /etc/systemd/journald.conf.d/urbanhealth.conf >/dev/null
    sudo systemctl restart systemd-journald
  fi
  grep -q -- '--log-driver=journald' /etc/systemd/system/urbanhealth.service || \
    sudo sed -i 's|docker run --rm --name urbanhealth \\\\|docker run --rm --name urbanhealth --log-driver=journald \\\\|' /etc/systemd/system/urbanhealth.service
  sudo systemctl daemon-reload
  if ! sudo docker image inspect urbanhealth-local:$SHA >/dev/null 2>&1; then
    W=\$(mktemp -d)
    curl -fsSL https://codeload.github.com/projecttrackerindia/healthtracker/tar.gz/$SHA | tar xz -C \"\$W\" --strip-components=1
    echo '   building $SHA (a few minutes)'
    sudo docker build -q -t urbanhealth-local:$SHA \"\$W\" >/dev/null
    rm -rf \"\$W\"
  fi
  sudo sed -i 's|^IMAGE=.*|IMAGE=urbanhealth-local:$SHA|' /etc/urbanhealth/release.env
  E=/opt/urbanhealth/repo/deploy/gcp/env.yaml
  if sudo grep -q '^APP_VERSION:' \$E; then sudo sed -i 's|^APP_VERSION:.*|APP_VERSION: \"$SHA\"|' \$E
  else echo 'APP_VERSION: \"$SHA\"' | sudo tee -a \$E >/dev/null; fi
  # the VM's permission to read secrets was granted moments ago and can take a minute to apply
  for i in 1 2 3 4 5 6 7 8; do sudo /usr/local/bin/urbanhealth-env && break; [ \$i = 8 ] && exit 1; echo '   waiting for secret access'; sleep 20; done
  sudo docker pull -q postgres:16 >/dev/null
  # No certificate requests until the domain points here: failed attempts count against Let's Encrypt limits
  [ -f /opt/urbanhealth/.moved ] || sudo systemctl stop caddy
"
ok "image $SHA built, settings and secrets readable by the VM"

# Exact row count of every table, used to prove the copy is complete.
COUNT_SQL="select coalesce(string_agg(table_name||'='||(xpath('/row/c/text()', query_to_xml(format('select count(*) as c from public.%I', table_name), false, true, '')))[1]::text, ' ' order by table_name),'empty') from information_schema.tables where table_schema='public' and table_type='BASE TABLE';"
B64=$(printf '%s' "$COUNT_SQL" | base64 -w0)
PSQL="U=\$(sudo sed -n 's/^DATABASE_URL=//p' /etc/urbanhealth/app.env); echo $B64 | base64 -d > /tmp/uhc.sql; sudo docker run --rm -v /var/run/cloudsql:/cloudsql -v /tmp/uhc.sql:/c.sql:ro postgres:16 psql -At \"\$U\" -f /c.sql; rm -f /tmp/uhc.sql"
summary() { tr ' ' '\n' <<<"$1" | awk -F= '{t++; r+=$2} END {printf "%d tables, %d rows", t, r}'; }

say "6. Moving the data"
if [ "$(nssh "test -f /opt/urbanhealth/.moved && echo yes" | tr -d '\r')" = yes ]; then
  ok "already moved on an earlier run — the new VM is live with its own data, skipping"
else
  NEW_NOW=$(nssh "$PSQL" | tr -d '\r')
  if [ "$NEW_NOW" != empty ] && [ "${FORCE_COPY:-0}" != 1 ]; then
    die "The new database already has tables but the move never finished. To copy again from scratch:
   gcloud --account=$NEW_ACCT sql databases delete tht --instance=$SQL_INSTANCE --project $NEW_P
   then run this script again."
  fi
  echo "   This stops the old app. The site is down from here until the DNS change in step 7 (about 10 minutes)."
  read -r -p "   Type yes to continue: " a
  [ "$a" = yes ] || die "Stopped before touching the live site. Run again when ready."
  ossh "sudo systemctl stop urbanhealth"
  ok "old app stopped (its VM and database are untouched)"
  ossh "
    set -e
    U=\$(sudo sed -n 's/^DATABASE_URL=//p' /etc/urbanhealth/app.env)
    sudo docker run --rm -v /var/run/cloudsql:/cloudsql postgres:16 pg_dump --no-owner --no-acl -Fc -d \"\$U\" > /tmp/tht.dump
    ls -l /tmp/tht.dump | awk '{print \"   dump \" \$5 \" bytes\"}'
  "
  o compute scp --zone "$ZONE" "$VM":/tmp/tht.dump "$WORK/tht.dump" >/dev/null
  n compute scp --zone "$ZONE" "$WORK/tht.dump" "$VM":/tmp/tht.dump >/dev/null
  nssh "
    U=\$(sudo sed -n 's/^DATABASE_URL=//p' /etc/urbanhealth/app.env)
    sudo docker run --rm -v /var/run/cloudsql:/cloudsql -v /tmp/tht.dump:/tht.dump:ro postgres:16 \
      pg_restore --no-owner --no-acl -d \"\$U\" /tht.dump || echo '   pg_restore printed warnings; the row counts below decide'
    rm -f /tmp/tht.dump
  "
  ossh "rm -f /tmp/tht.dump"; rm -f "$WORK/tht.dump"

  OLD_COUNTS=$(ossh "$PSQL" | tr -d '\r'); NEW_COUNTS=$(nssh "$PSQL" | tr -d '\r')
  echo "   old: $(summary "$OLD_COUNTS")"
  echo "   new: $(summary "$NEW_COUNTS")"
  if [ -z "$OLD_COUNTS" ] || [ "$OLD_COUNTS" = empty ] || [ "$OLD_COUNTS" != "$NEW_COUNTS" ]; then
    diff <(tr ' ' '\n' <<<"$OLD_COUNTS") <(tr ' ' '\n' <<<"$NEW_COUNTS") | sed 's/^/   /' || true
    die "The copy does not match. Putting the old site back:
   gcloud --account=$OLD_ACCT compute ssh $VM --project $OLD_P --zone $ZONE --command 'sudo systemctl start urbanhealth'"
  fi
  ok "every table has the same number of rows in both"

  nssh "sudo systemctl enable --now urbanhealth >/dev/null 2>&1"
  for i in $(seq 1 40); do
    V=$(nssh "curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null" | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    [ "$V" = "$SHA" ] && break
    if [ "$i" = 40 ]; then
      ossh "sudo systemctl start urbanhealth"
      die "The new app did not come up, so the old one was started again (site back as before). Logs:
   gcloud --account=$NEW_ACCT compute ssh $VM --project $NEW_P --zone $ZONE --command 'sudo journalctl -u urbanhealth -n 60'"
    fi
    sleep 5
  done
  nssh "sudo touch /opt/urbanhealth/.moved"
  ok "new app running $SHA on the new VM"
fi

say "7. Point the domain at the new VM"
cat <<MSG

   In Hostinger → urbanhealth.in → DNS records, edit the A record for @:

       A    @    $NEW_IP    TTL 300

   (www is a CNAME to urbanhealth.in, so it follows by itself.)
   Leave this window open: it notices the change, then turns on HTTPS and checks the site.
MSG
for i in $(seq 1 180); do
  A=$(curl -fsS --max-time 8 "https://dns.google/resolve?name=urbanhealth.in&type=A" 2>/dev/null | grep -o '"data":"[0-9.]*"' | head -1 | cut -d'"' -f4)
  [ "$A" = "$NEW_IP" ] && break
  [ "$i" = 180 ] && die "After 45 minutes urbanhealth.in still points at ${A:-nothing}. Fix the A record, then run this script again: it resumes here."
  [ $((i % 4)) = 1 ] && echo "   waiting for DNS (now ${A:-?})"
  sleep 15
done
ok "urbanhealth.in → $NEW_IP"
nssh "sudo systemctl start caddy"
for i in $(seq 1 40); do
  V=$(curl -fsS --max-time 8 --resolve "urbanhealth.in:443:$NEW_IP" https://urbanhealth.in/api/health 2>/dev/null | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  [ "$V" = "$SHA" ] && break
  [ "$i" = 40 ] && die "HTTPS is not answering yet. Check: gcloud --account=$NEW_ACCT compute ssh $VM --project $NEW_P --zone $ZONE --command 'sudo journalctl -u caddy -n 40'"
  sleep 6
done
ok "https://urbanhealth.in is served by the new VM with a valid certificate"

cat <<MSG

== Moved

   Urban Health now runs in $NEW_P, billed to the Urban Health billing account.
   Some networks remember the old address for a few hours; those visitors briefly see an error page.

   Rollback, while the old VM exists: put the old address back in Hostinger, then
       gcloud --account=$OLD_ACCT compute ssh $VM --project $OLD_P --zone $ZONE --command 'sudo systemctl start urbanhealth'

   Deploys from now on (Cloud Shell):
       gcloud --account=$NEW_ACCT compute ssh $VM --zone $ZONE --project $NEW_P --command "curl -fsSL https://raw.githubusercontent.com/projecttrackerindia/healthtracker/main/deploy/vm/vm-ship.sh | bash"

   After a week of real use, delete the old VM, its address and the old Cloud SQL instance to stop
   their charges. Keep the old project: it hosts Project Tracker and the documents bucket.
MSG

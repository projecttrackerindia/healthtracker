#!/usr/bin/env bash
# One-time: create the VM that serves urbanhealth.in. Safe to re-run — every step checks first, and
# re-running on an existing VM just re-applies the bootstrap.
#
# It does NOT touch Cloud SQL, Secret Manager, billing or the Cloud Run service. The Cloud Run service keeps
# serving until DNS moves, which is what makes the cutover reversible.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh
exists() { "$@" >/dev/null 2>&1; }
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

gcloud config set project "$PROJECT_ID" >/dev/null

say "Service account for the VM"
# Least privilege: read images, read secrets, reach Cloud SQL. Nothing else — this identity is reachable by
# anything that gets onto the box.
if ! exists gcloud iam service-accounts describe "$VM_SA"; then
  gcloud iam service-accounts create "${VM}-vm" --display-name="Urban Health VM"
fi
for r in roles/artifactregistry.reader roles/secretmanager.secretAccessor roles/cloudsql.client roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$VM_SA" --role="$r" --condition=None >/dev/null
done

say "Reserved address"
# Reserved, not ephemeral. An ephemeral IP changes if the VM is ever stopped, which would silently break DNS
# — and a reserved one is what a load balancer migration later needs to not be a second DNS change.
exists gcloud compute addresses describe "$IP_NAME" --region "$REGION" || \
  gcloud compute addresses create "$IP_NAME" --region "$REGION"
IP=$(gcloud compute addresses describe "$IP_NAME" --region "$REGION" --format='value(address)')
echo "   $IP"

say "Firewall"
exists gcloud compute firewall-rules describe "${VM}-web" || \
  gcloud compute firewall-rules create "${VM}-web" --allow=tcp:80,tcp:443 \
    --target-tags="${VM}" --description="HTTP/HTTPS to the Urban Health VM"
# Google's health-check probes come from these two ranges. Opened now so adding a load balancer later needs
# no firewall change at all.
exists gcloud compute firewall-rules describe "${VM}-healthcheck" || \
  gcloud compute firewall-rules create "${VM}-healthcheck" --allow=tcp:80 \
    --source-ranges=130.211.0.0/22,35.191.0.0/16 --target-tags="${VM}" \
    --description="Google load balancer health checks (unused until a load balancer exists)"

say "VM"
if ! exists gcloud compute instances describe "$VM" --zone "$ZONE"; then
  gcloud compute instances create "$VM" --zone "$ZONE" --machine-type "$MACHINE" \
    --image-family=debian-12 --image-project=debian-cloud \
    --boot-disk-size="${DISK_GB}GB" --boot-disk-type=pd-balanced \
    --service-account="$VM_SA" --scopes=https://www.googleapis.com/auth/cloud-platform \
    --address="$IP" --tags="${VM}" --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring
else
  echo "   already there"
fi

say "Bootstrap"
gcloud compute scp --zone "$ZONE" bootstrap.sh urbanhealth-env release.sh Caddyfile "$VM":/tmp/ --quiet
gcloud compute ssh "$VM" --zone "$ZONE" --quiet --command "
  set -e
  sudo install -m 0755 /tmp/urbanhealth-env /usr/local/bin/urbanhealth-env
  sudo install -m 0755 /tmp/release.sh /usr/local/bin/urbanhealth-release
  sudo install -m 0644 /tmp/Caddyfile /etc/caddy/Caddyfile 2>/dev/null || true
  sudo bash /tmp/bootstrap.sh '$PROJECT_ID' '$SQL_CONN' '$IMAGE' '$DOMAINS' '${ADMIN_EMAIL:-}'
  sudo install -m 0644 /tmp/Caddyfile /etc/caddy/Caddyfile
  sudo systemctl reload caddy || sudo systemctl restart caddy
"

cat <<MSG

== Provisioned

  VM        $VM ($MACHINE, $ZONE)
  Address   $IP

Point DNS at it, with a short TTL so the cutover and any rollback are quick:

  A     @     $IP     TTL 300
  A     www   $IP     TTL 300

Caddy issues the certificate on the first request after DNS resolves, so the
site answers with a certificate warning for a minute or two and then stops.
That is Let's Encrypt working, not a fault.

The Cloud Run service keeps running and keeps serving. Leave it up for a few
days: if anything here misbehaves, moving DNS back is the whole rollback.
MSG

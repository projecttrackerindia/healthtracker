#!/usr/bin/env bash
# One-time Google Cloud setup for Urban Health. Safe to re-run: every step checks first.
#   gcloud auth login && gcloud config set account YOU@gmail.com
#   export BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX     # gcloud billing accounts list
#   cp .env.example .env  &&  edit .env              # values from Railway
#   ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh
: "${BILLING_ACCOUNT:?set BILLING_ACCOUNT (gcloud billing accounts list)}"
[ -f .env ] || { echo "Create deploy/gcp/.env from .env.example first"; exit 1; }
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }

say "Project $PROJECT_ID"
exists gcloud projects describe "$PROJECT_ID" || gcloud projects create "$PROJECT_ID" --name="Urban Health"
gcloud beta billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT" >/dev/null
gcloud config set project "$PROJECT_ID" >/dev/null

say "APIs"
gcloud services enable run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  cloudbuild.googleapis.com storage.googleapis.com iamcredentials.googleapis.com cloudscheduler.googleapis.com logging.googleapis.com monitoring.googleapis.com

say "Service accounts"
exists gcloud iam service-accounts describe "$RUN_SA" || gcloud iam service-accounts create "${SERVICE}-run" --display-name="Urban Health app"
exists gcloud iam service-accounts describe "$DEPLOY_SA" || gcloud iam service-accounts create "${SERVICE}-deploy" --display-name="Urban Health deploys (GitHub)"
for r in roles/cloudsql.client roles/secretmanager.secretAccessor roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$RUN_SA" --role="$r" --condition=None >/dev/null
done
for r in roles/run.admin roles/artifactregistry.writer roles/cloudbuild.builds.editor roles/storage.admin roles/secretmanager.viewer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$DEPLOY_SA" --role="$r" --condition=None >/dev/null
done
gcloud iam service-accounts add-iam-policy-binding "$RUN_SA" --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser >/dev/null

# new projects: Cloud Build runs as the compute service account, which has no storage/registry/logging rights by default
PN=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
for r in roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${PN}-compute@developer.gserviceaccount.com" --role="$r" --condition=None >/dev/null
done

say "Artifact Registry"
exists gcloud artifacts repositories describe "$REPO" --location="$REGION" || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" --description="Urban Health images"

say "Cloud SQL (Postgres 16, $REGION, daily backups + point-in-time recovery)"
if ! exists gcloud sql instances describe "$SQL_INSTANCE"; then
  gcloud sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 --edition=ENTERPRISE --region="$REGION" --tier="$SQL_TIER" \
    --storage-type=SSD --storage-size=20 --storage-auto-increase --availability-type=zonal \
    --backup-start-time=21:30 --enable-point-in-time-recovery --retained-backups-count=14 --deletion-protection
fi
exists gcloud sql databases describe "$DB_NAME" --instance="$SQL_INSTANCE" || gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE"
DB_PASS_FILE=.dbpass
if [ -z "$(gcloud sql users list --instance="$SQL_INSTANCE" --filter="name=$DB_USER" --format='value(name)')" ]; then
  openssl rand -base64 30 | tr -d '/+=\n' > "$DB_PASS_FILE"; chmod 600 "$DB_PASS_FILE"
  gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$(cat "$DB_PASS_FILE")"
  echo "Database password saved to deploy/gcp/$DB_PASS_FILE (git-ignored). Keep it safe."
fi
CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"

say "Documents bucket gs://$BUCKET (private, Mumbai)"
exists gcloud storage buckets describe "gs://$BUCKET" || \
  gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$RUN_SA" --role=roles/storage.objectAdmin >/dev/null
# the app talks to the bucket with the S3 API; Google's S3 interop needs an HMAC key for the app's service account
if ! grep -q '^S3_ACCESS_KEY=.\+' .env; then
  OUT=$(gcloud storage hmac create "$RUN_SA" --format="value(metadata.accessId,secret)")
  AK=$(echo "$OUT" | cut -f1); SK=$(echo "$OUT" | cut -f2)
  sed -i "s|^S3_ACCESS_KEY=.*|S3_ACCESS_KEY=$AK|; s|^S3_SECRET_KEY=.*|S3_SECRET_KEY=$SK|" .env
  echo "Bucket HMAC key written to .env"
fi
if ! grep -q '^DATABASE_URL=.\+' .env && [ -f "$DB_PASS_FILE" ]; then
  # Cloud Run reaches Cloud SQL over a unix socket: no public IP, no firewall rules
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$(cat "$DB_PASS_FILE")@/$DB_NAME?host=/cloudsql/$CONN|" .env
fi

say "Secret Manager"
grep -v '^\s*#' secrets.txt | grep -v '^\s*$' | while read -r name; do
  val=$(grep "^${name}=" .env | head -1 | cut -d= -f2- || true)
  [ -n "$val" ] || { echo "  skip $name (empty in .env)"; continue; }
  if exists gcloud secrets describe "$name"; then
    printf '%s' "$val" | gcloud secrets versions add "$name" --data-file=- >/dev/null; echo "  updated $name"
  else
    printf '%s' "$val" | gcloud secrets create "$name" --replication-policy=user-managed --locations="$REGION" --data-file=- >/dev/null; echo "  created $name"
  fi
done

say "GitHub → Google keyless login (Workload Identity Federation)"
PN=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
exists gcloud iam workload-identity-pools describe github --location=global || \
  gcloud iam workload-identity-pools create github --location=global --display-name="GitHub Actions"
exists gcloud iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github || \
  gcloud iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github \
    --display-name="GitHub" --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}" >/dev/null
WIF="projects/${PN}/locations/global/workloadIdentityPools/github/providers/github"

say "Done"
cat <<MSG
GitHub → Settings → Secrets and variables → Actions, add:
  Secrets:    GCP_WIF_PROVIDER = $WIF
              GCP_DEPLOY_SA    = $DEPLOY_SA
  Variables:  GCP_PROJECT_ID   = $PROJECT_ID     GCP_REGION = $REGION
Next:
  1. ./deploy.sh                     # builds the image and deploys to Cloud Run (a *.run.app address)
  2. ./migrate_data.sh               # rehearse copying Railway's database + documents (safe: read-only on Railway)
  3. See GOOGLE_CLOUD.md             # test, then the cut-over window and DNS
MSG

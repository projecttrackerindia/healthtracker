#!/usr/bin/env bash
# Let GitHub Actions deploy to this project without a stored key (Workload Identity Federation).
#
# Why this exists separately from setup.sh: setup.sh is a first-run script for an empty project. It links
# billing, creates Cloud SQL instances, and — the dangerous part — rewrites every Secret Manager value from a
# local .env. Re-running it against a live project to pick up one missing piece would overwrite production
# secrets with whatever happened to be in a developer's .env file. This script touches nothing but the three
# WIF objects, and each step checks first, so it is safe to run as often as you like.
#
#   ./wif.sh
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=config.sh
source ./config.sh

gcloud config set project "$PROJECT_ID" >/dev/null
PN=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
exists() { "$@" >/dev/null 2>&1; }

if ! exists gcloud iam service-accounts describe "$DEPLOY_SA"; then
  echo "The deploy service account does not exist yet:"
  echo "  $DEPLOY_SA"
  echo "Create it and grant it the deploy roles — the 'Service accounts' block in setup.sh is the reference."
  exit 1
fi

echo "== Pool"
exists gcloud iam workload-identity-pools describe github --location=global \
  && echo "   already there" \
  || gcloud iam workload-identity-pools create github --location=global --display-name="GitHub Actions"

echo "== Provider"
# The attribute condition is the security boundary: without it, ANY repository on GitHub could mint a token
# for this service account. It pins the trust to this one repository.
exists gcloud iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github \
  && echo "   already there" \
  || gcloud iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github \
       --display-name="GitHub" --issuer-uri="https://token.actions.githubusercontent.com" \
       --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
       --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

echo "== Binding"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}" >/dev/null
echo "   ok"

cat <<MSG

Paste these into GitHub → Settings → Secrets and variables → Actions:

  Secret    GCP_WIF_PROVIDER  projects/${PN}/locations/global/workloadIdentityPools/github/providers/github
  Secret    GCP_DEPLOY_SA     ${DEPLOY_SA}
  Variable  GCP_PROJECT_ID    ${PROJECT_ID}
  Variable  GCP_REGION        ${REGION}

Then merge anything to main. The run deploys and goes red unless /api/health
comes back reporting that exact commit.
MSG

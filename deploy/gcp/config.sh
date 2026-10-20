# Shared settings for the Google Cloud scripts. Edit the first block once; everything else follows.
# shellcheck shell=bash
export PROJECT_ID="${PROJECT_ID:-thehealthtracker-prod}"   # must be globally unique
export REGION="${REGION:-asia-south1}"                      # Mumbai (asia-south2 = Delhi)
export SERVICE="${SERVICE:-tht}"
export REPO="${REPO:-tht}"                                  # Artifact Registry repository
export SQL_INSTANCE="${SQL_INSTANCE:-tht-pg}"
export SQL_TIER="${SQL_TIER:-db-g1-small}"                  # lean; production HA: db-custom-1-3840 with --availability-type=REGIONAL
export DB_NAME="${DB_NAME:-tht}"
export DB_USER="${DB_USER:-tht}"
export BUCKET="${BUCKET:-${PROJECT_ID}-documents}"          # private bucket for uploaded documents
export RUN_SA="${SERVICE}-run@${PROJECT_ID}.iam.gserviceaccount.com"       # identity of the running app
export DEPLOY_SA="${SERVICE}-deploy@${PROJECT_ID}.iam.gserviceaccount.com" # identity GitHub Actions uses
export IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:latest}"
export GITHUB_REPO="${GITHUB_REPO:-projecttrackerindia/healthtracker}"

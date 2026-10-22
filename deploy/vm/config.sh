# Settings for the Compute Engine host. Sourced by every script in this directory.
# shellcheck shell=bash
export PROJECT_ID="${PROJECT_ID:-central-weft-511003-c1}"
export REGION="${REGION:-asia-south1}"              # Mumbai, same as Cloud Run and Cloud SQL
export ZONE="${ZONE:-asia-south1-a}"
export VM="${VM:-urbanhealth}"
export MACHINE="${MACHINE:-e2-small}"               # 2 shared vCPU, 2 GB — matches the 1 CPU / 1 GiB Cloud Run had
export DISK_GB="${DISK_GB:-20}"
export IP_NAME="${IP_NAME:-urbanhealth-ip}"         # reserved, not ephemeral: a load balancer later must not move it
export DOMAINS="${DOMAINS:-urbanhealth.in www.urbanhealth.in}"
export SQL_INSTANCE="${SQL_INSTANCE:-tht-pg}"
export SQL_CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
export VM_SA="${VM:-urbanhealth}-vm@${PROJECT_ID}.iam.gserviceaccount.com"
export IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/tht/tht:latest}"

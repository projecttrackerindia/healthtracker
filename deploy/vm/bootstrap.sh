#!/usr/bin/env bash
# Runs on the VM, as root, at first boot and again on every provision.sh run. Idempotent.
#
# Installs Docker, the Cloud SQL Auth Proxy and Caddy, and writes the three systemd units that keep the app
# alive. Nothing here is specific to a release — releases happen in release.sh.
set -euo pipefail

PROJECT_ID="$1"; SQL_CONN="$2"; IMAGE="$3"; DOMAINS="$4"; ADMIN_EMAIL="${5:-}"

echo "== Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg debian-keyring debian-archive-keyring apt-transport-https

if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io
fi

if ! command -v caddy >/dev/null; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
fi

if [ ! -x /usr/local/bin/cloud-sql-proxy ]; then
  curl -fsSL -o /usr/local/bin/cloud-sql-proxy \
    "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64"
  chmod +x /usr/local/bin/cloud-sql-proxy
fi

echo "== Directories"
# The app's DATABASE_URL says host=/cloudsql/<conn>, exactly as it did on Cloud Run. The proxy puts a unix
# socket there and the container mounts it at the same path, so the connection string never changes and
# there is nothing to get wrong during the move.
install -d -m 0755 /var/run/cloudsql /var/log/caddy /opt/urbanhealth/data
install -d -m 0700 /etc/urbanhealth

echo "== Release settings"
cat > /etc/urbanhealth/release.env <<EOF
PROJECT_ID=$PROJECT_ID
SQL_CONN=$SQL_CONN
IMAGE=$IMAGE
EOF

echo "== Caddy"
install -d -m 0755 /etc/caddy
cat > /etc/caddy/caddy.env <<EOF
DOMAINS=$DOMAINS
ADMIN_EMAIL=$ADMIN_EMAIL
EOF
sed -i '/^EnvironmentFile=\/etc\/caddy\/caddy.env$/d' /lib/systemd/system/caddy.service 2>/dev/null || true
mkdir -p /etc/systemd/system/caddy.service.d
cat > /etc/systemd/system/caddy.service.d/override.conf <<'EOF'
[Service]
EnvironmentFile=/etc/caddy/caddy.env
EOF

echo "== Units"
cat > /etc/systemd/system/cloud-sql-proxy.service <<EOF
[Unit]
Description=Cloud SQL Auth Proxy
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/cloud-sql-proxy --unix-socket /var/run/cloudsql $SQL_CONN
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/urbanhealth.service <<'EOF'
[Unit]
Description=Urban Health
Requires=cloud-sql-proxy.service docker.service
After=cloud-sql-proxy.service docker.service

[Service]
EnvironmentFile=/etc/urbanhealth/release.env
# Secrets are fetched fresh on every start rather than baked into the machine image, so rotating one in
# Secret Manager and restarting is the whole procedure. The file is 0600 and never leaves the VM.
ExecStartPre=/usr/local/bin/urbanhealth-env
ExecStartPre=-/usr/bin/docker rm -f urbanhealth
ExecStart=/usr/bin/docker run --rm --name urbanhealth \
  --env-file /etc/urbanhealth/app.env \
  -v /var/run/cloudsql:/cloudsql \
  -v /opt/urbanhealth/data:/app/data \
  -p 127.0.0.1:8080:8080 \
  ${IMAGE}
ExecStop=/usr/bin/docker stop urbanhealth
Restart=always
RestartSec=5
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now cloud-sql-proxy caddy >/dev/null
echo "== Bootstrap done"

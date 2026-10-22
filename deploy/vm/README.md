# Hosting Urban Health on a VM

## Why move off Cloud Run

Cloud Run has no IP address, so a custom domain needs either a domain mapping — **not available in
`asia-south1`**, and Preview-only in any case — or a load balancer at roughly ₹1,500–2,000 a month.

But look at how the service was actually configured:

```
--min-instances 1 --max-instances 1 --no-cpu-throttling
```

That is a single always-on container that never scales, because video-call rooms and the daily jobs live
inside the one process and WebSocket calls need hour-long requests. So we were already running one box. We
were running it on the product that charges a premium for elasticity, with the elasticity switched off, and
that same product is the one that cannot take a domain.

A VM is the honest version of what we were already doing, and the domain becomes one `A` record.

## What runs on the box

| | |
| --- | --- |
| **Caddy** | TLS. Gets certificates from Let's Encrypt on first request and renews them itself — no cron, no expiry to diarise. Reverse-proxies to `127.0.0.1:8080`. |
| **`urbanhealth.service`** | The same container image the Cloud Run deploy built. Not a rebuild, not a port — the Dockerfile was already host-agnostic. |
| **`cloud-sql-proxy.service`** | Puts a unix socket at `/var/run/cloudsql`, mounted into the container at `/cloudsql`. `DATABASE_URL` keeps saying `host=/cloudsql/<conn>` exactly as it did on Cloud Run, so the connection string never changes. |
| **`urbanhealth-env`** | Rebuilds `/etc/urbanhealth/app.env` from `env.yaml` plus Secret Manager on every start. Rotating a secret is: add a version, restart. |

The app binds to `127.0.0.1` only. Nothing but Caddy can reach it, even from inside the VPC.

## Cutover

1. `cd deploy/vm && ./provision.sh` — prints the reserved IP.
2. In Hostinger, replace the parking records:
   `A @ <ip> TTL 300` and `A www <ip> TTL 300`.
   **Short TTL on purpose**: it makes both the cutover and the rollback minutes rather than hours.
3. Wait for the certificate. The first request after DNS resolves triggers issuance; until it completes the
   site shows a certificate warning. That is Let's Encrypt working, not a fault.
4. Check, do not assume:
   ```
   curl -sI  https://urbanhealth.in/            | grep -i 'strict-transport'
   curl -s   https://urbanhealth.in/api/health
   curl -s   https://urbanhealth.in/robots.txt
   curl -sI  https://www.urbanhealth.in/        | grep -i location   # expect 308 to the apex
   ```
5. **Leave Cloud Run running for a few days.** While it is up, rollback is moving DNS back — nothing else.
   Delete it only once the VM has carried real traffic through a weekday.

`RP_ID` becomes live at this point, so every passkey made on a Cloud Run URL stops working. There are no
real users yet, so this costs nothing today and never will again.

## Adding a load balancer later

The VM stays. The load balancer goes **in front** of it. Nothing in the application changes.

1. Unmanaged instance group containing the VM, health check on `/api/health`.
2. Backend service → URL map → target HTTPS proxy with a Google-managed certificate → global forwarding rule
   on a new global IP.
3. Caddy's block becomes `:80 { reverse_proxy 127.0.0.1:8080 }` — the load balancer terminates TLS now.
4. Point DNS at the load balancer's IP. That short TTL earns its keep a second time.

Two things were done up front so this stays a half-hour job rather than a rebuild: the VM's address is
**reserved** rather than ephemeral, and the firewall already admits Google's health-check ranges
(`130.211.0.0/22`, `35.191.0.0/16`).

Worth adding when you want **Cloud Armor** (rate limiting and OWASP rules), **Cloud CDN**, or more than one
VM. Before that it is cost with no benefit.

## Operating it

```
sudo systemctl status urbanhealth
sudo journalctl -u urbanhealth -f
sudo journalctl -u cloud-sql-proxy -n 50
sudo systemctl restart urbanhealth      # also re-reads secrets
```

Unattended security upgrades are on by default in Debian 12. The container restarts on crash
(`Restart=always`) and on reboot (`WantedBy=multi-user.target`).

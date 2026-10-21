"""TheHealthTracker web server (FastAPI) for Railway.

* Serves the static web app from ./web with pre-compressed (br / gzip) variants, long-lived caching for
  fingerprinted assets and a strict set of security headers.
* Exposes /healthz for Railway's health check and a small versioned JSON API under /api/v1.

Run locally:   uvicorn server:app --reload
On Railway:    the Procfile / railway.json start command uses $PORT.
"""
from __future__ import annotations

import gzip
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from sqlalchemy.exc import OperationalError

from api.db import Base, engine, ensure_columns, ensure_indexes, session
from api import admin as admin_api, auth as auth_api, family as family_api, more as more_api, reminders, routes as public_api
from api.seed import seed_all

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
ADMIN = ROOT / "admin"
SITE = ROOT / "site"
VERSION = os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev")[:8]
STARTED = time.time()

app = FastAPI(title="TheHealthTracker", version=VERSION, docs_url=None, redoc_url=None, openapi_url="/api/v1/openapi.json")
# Nothing compressed API responses before this: the phrase table, places and store lists all went out raw.
# GZipMiddleware skips anything that already carries Content-Encoding, so the pre-built .br variants below
# are untouched - this only catches what they miss, including /app for a client that does not accept brotli.
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
app.add_middleware(GZipMiddleware, minimum_size=1024)

# --------------------------------------------------------------------------------------------------
# Pre-compressed copies are only served when they match their source byte for byte. An index.html edited
# without re-running tools/compress.py would otherwise keep sending the OLD page to every browser.
# --------------------------------------------------------------------------------------------------
try:
    import brotli as _brotli  # type: ignore
except ImportError:  # without the module we cannot verify .br files, so we never serve them
    _brotli = None


def _verified_variants() -> set[Path]:
    ok: set[Path] = set()
    for base in (WEB, SITE):
        for alt in list(base.rglob("*.br")) + list(base.rglob("*.gz")):
            src = alt.with_suffix("")
            if not src.is_file():
                continue
            try:
                raw = alt.read_bytes()
                if alt.suffix == ".br":
                    if _brotli is None or _brotli.decompress(raw) != src.read_bytes():
                        continue
                elif gzip.decompress(raw) != src.read_bytes():
                    continue
            except Exception:
                continue
            ok.add(alt)
    return ok


VARIANTS = _verified_variants()
_skipped = [str(a.relative_to(ROOT)) for b in (WEB, SITE) for a in list(b.rglob("*.br")) + list(b.rglob("*.gz")) if a not in VARIANTS]
if _skipped:
    print(f"[TheHealthTracker] WARNING: {len(_skipped)} stale compressed file(s) ignored; run tools/compress.py: {', '.join(_skipped[:5])}", flush=True)


def _variant(p: Path, request: Request) -> tuple[Path, str | None]:
    ae = request.headers.get("accept-encoding", "")
    for enc, suf in (("br", ".br"), ("gzip", ".gz")):
        alt = p.with_name(p.name + suf)
        if enc in ae and alt in VARIANTS:
            return alt, enc
    return p, None



@app.on_event("startup")
def _init_db():
    try:
        Base.metadata.create_all(engine)
    except OperationalError as e:
        if "already exists" not in str(e):
            raise
    ensure_columns()
    ensure_indexes()
    with session() as db:
        seed_all(db)
        try:
            shop_api.ensure_shop(db)
        except Exception as e:
            print("[shop] seed failed:", str(e)[:160], flush=True)
    reminders.start()
    proactive_api.start()


app.include_router(public_api.r)
app.include_router(auth_api.r)
app.include_router(family_api.r)
app.include_router(more_api.r)
app.include_router(admin_api.r)
from api import places as places_api, billing as billing_api, inbox as inbox_api, partner as partner_api  # noqa: E402
app.include_router(places_api.r)
app.include_router(billing_api.r)
app.include_router(inbox_api.r)
app.include_router(partner_api.r)
from api import consult as consult_api  # noqa: E402
app.include_router(consult_api.r)
app.include_router(consult_api.pr)
app.include_router(consult_api.ws)
from api import proactive as proactive_api  # noqa: E402
from api import tasks as tasks_api  # noqa: E402
app.include_router(proactive_api.r)
app.include_router(tasks_api.r)
from api import abdm as abdm_api, export as export_api, medid as medid_api, network as network_api  # noqa: E402
app.include_router(medid_api.r)
app.include_router(export_api.r)
app.include_router(network_api.r)
app.include_router(network_api.ar)
app.include_router(abdm_api.r)
from api import upipay as upipay_api  # noqa: E402
app.include_router(upipay_api.r)
app.include_router(upipay_api.ar)
from api import digilocker as digilocker_api  # noqa: E402
app.include_router(digilocker_api.r)
from api import apps as apps_api, fitbit as fitbit_api, shop as shop_api, wearables as wear_api  # noqa: E402
app.include_router(apps_api.r)
app.include_router(fitbit_api.r)
app.include_router(wear_api.r)
from api import sos as sos_api  # noqa: E402
app.include_router(sos_api.r)
from api import summary as summary_api  # noqa: E402
app.include_router(summary_api.r)
from api import backup as backup_api  # noqa: E402
app.include_router(backup_api.r)
from api import i18n as i18n_api  # noqa: E402
app.include_router(i18n_api.r)
app.include_router(shop_api.r)
app.include_router(shop_api.ar)
from api import blood as blood_api  # noqa: E402
app.include_router(blood_api.r)
app.include_router(blood_api.pr)

# --------------------------------------------------------------------------------------------------
# Security headers. The app uses inline scripts/styles and a blob: web worker, WebGL and (for SOS)
# geolocation, so the CSP allows exactly that and nothing from other origins.
# --------------------------------------------------------------------------------------------------
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' blob: https://checkout.razorpay.com https://maps.googleapis.com https://www.gstatic.com https://www.google.com https://www.recaptcha.net; "
    "worker-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data: blob: https://i.ytimg.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://maps.googleapis.com https://maps.gstatic.com https://*.googleapis.com https://*.gstatic.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'self' wss: ws: blob: data: https://api.razorpay.com https://lumberjack.razorpay.com https://maps.googleapis.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://www.googleapis.com; "
    "media-src 'self' blob:; "
    "frame-src https://www.youtube-nocookie.com https://www.youtube.com https://api.razorpay.com https://checkout.razorpay.com https://www.google.com https://www.recaptcha.net https://*.firebaseapp.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(self), microphone=(self), display-capture=(), payment=(self), publickey-credentials-create=(self), publickey-credentials-get=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


# One address for the whole site. The sign-in cookie belongs to the exact host that set it, so someone who signs in on
# www.thehealthtracker.com and opens thehealthtracker.com/app (or the other way round) would look signed out.
CANONICAL = (os.getenv("CANONICAL_HOST") or "").strip().lower()  # e.g. thehealthtracker.com; set it only after both addresses resolve


@app.middleware("http")
async def headers(request: Request, call_next):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(":")[0].lower()
    if CANONICAL and host == "www." + CANONICAL and request.method in ("GET", "HEAD") and request.url.path != "/healthz":
        q = ("?" + request.url.query) if request.url.query else ""
        return Response(status_code=308, headers={"Location": f"https://{CANONICAL}{request.url.path}{q}"})
    # the website demo runs with a throw-away "demo-…" key: it may read, it may never order, book, pay, call or spend AI
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/v1/") and (request.headers.get("x-dokko-key") or "").startswith("demo-"):
        if request.url.path not in ("/api/v1/hello", "/api/v1/beacon"):
            return JSONResponse({"detail": "This is the demo — sign in to do this for your own family."}, status_code=403)
    resp: Response = await call_next(request)
    for k, v in SECURITY.items():
        resp.headers.setdefault(k, v)
    if os.getenv("APP_ENV", "production") != "production":
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


# --------------------------------------------------------------------------------------------------
# API (Phase 1 starts here; every route is versioned)
# --------------------------------------------------------------------------------------------------
@app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/api/health", methods=["GET", "HEAD"], include_in_schema=False)  # Cloud Run reserves /healthz at its front door
def healthz():
    return {"ok": True, "version": VERSION, "uptime_s": int(time.time() - STARTED)}


# --------------------------------------------------------------------------------------------------
# Static files with pre-compressed variants
# --------------------------------------------------------------------------------------------------
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".webmanifest": "application/manifest+json",
    ".bin": "application/octet-stream",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".webp": "image/webp",    # with X-Content-Type-Options: nosniff, Safari shows a broken image for a wrong type
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".avif": "image/avif",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".woff": "font/woff", ".ttf": "font/ttf", ".pdf": "application/pdf", ".apk": "application/vnd.android.package-archive",
}
COMPRESSIBLE = {".html", ".js", ".css", ".json", ".svg", ".webmanifest", ".txt"}
NO_CACHE = {"index.html", "sw.js", "manifest.webmanifest"}


def _safe(rel: str) -> Path:
    p = (WEB / rel).resolve()
    if WEB not in p.parents and p != WEB:
        raise HTTPException(404)
    return p


@app.api_route("/partner", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/partner/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def partner_page(rest: str = ""):
    return FileResponse(ROOT / "partner" / "index.html", media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache", "X-Frame-Options": "DENY"})


@app.api_route("/admin", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/admin/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def admin_page(rest: str = ""):
    return FileResponse(ADMIN / "index.html", media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache", "X-Frame-Options": "DENY"})


def _conditional(request: Request, r: FileResponse):
    """FileResponse sets an ETag, but starlette only honours If-None-Match inside StaticFiles, which this app
    does not mount. Without this, `no-cache` on the 400 KB app shell meant revalidate-and-resend on every open
    instead of a 304."""
    tag = r.headers.get("etag")
    inm = request.headers.get("if-none-match")
    if tag and inm and tag in [t.strip() for t in inm.split(",")]:
        keep = {k: v for k, v in r.headers.items() if k.lower() in ("etag", "cache-control", "vary", "content-encoding")}
        return Response(status_code=304, headers=keep)
    return r


def _send(p: Path, request: Request, cache: str):
    ext = p.suffix.lower()
    headers = {"Vary": "Accept-Encoding", "Cache-Control": cache}
    path = p
    if ext in COMPRESSIBLE:
        path, enc = _variant(p, request)
        if enc:
            headers["Content-Encoding"] = enc
    # stat_result up front: without it starlette sets the ETag during __call__, i.e. after we would have
    # looked for it, and every conditional request falls through to a full resend.
    return _conditional(request, FileResponse(path, media_type=TYPES.get(ext, "application/octet-stream"),
                                              headers=headers, stat_result=os.stat(path)))


# landing page (public) at "/", the app at "/app"
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/signin", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/signup", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/reset", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/join/{token}", methods=["GET", "HEAD"], include_in_schema=False)
def landing(request: Request, token: str = ""):
    return _send(SITE / "index.html", request, "no-cache")


# privacy policy and terms: legal details come from Railway variables so they can change without a code change
LEGAL = {
    "ENTITY": os.getenv("LEGAL_ENTITY", "TheHealthTracker"),
    "ADDRESS": os.getenv("LEGAL_ADDRESS", "Hyderabad, Telangana, India"),
    "GRIEVANCE_NAME": os.getenv("GRIEVANCE_NAME", "Grievance Officer, TheHealthTracker"),
    "GRIEVANCE_EMAIL": os.getenv("GRIEVANCE_EMAIL") or os.getenv("SUPPORT_EMAIL") or os.getenv("ADMIN_EMAIL", ""),
    "SUPPORT_EMAIL": os.getenv("SUPPORT_EMAIL") or os.getenv("ADMIN_EMAIL", ""),
    "UPDATED": os.getenv("POLICY_UPDATED", "18 October 2026"),
}


@app.api_route("/privacy", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/terms", methods=["GET", "HEAD"], include_in_schema=False)
def legal_page(request: Request):
    import html as _html
    s = (SITE / (request.url.path.strip("/") + ".html")).read_text(encoding="utf-8")
    for k, v in LEGAL.items():
        s = s.replace("{{" + k + "}}", _html.escape(v))
    return Response(s, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})


@app.api_route("/d/{token}", methods=["GET", "HEAD"], include_in_schema=False)
def shared_doc(token: str, request: Request, raw: str = ""):
    """A document shared with a doctor by link: a small viewer page, or the file itself with ?raw=1."""
    import html as _html

    from api.db import session as _session
    from api.more import shared_file

    with _session() as db:
        s, got = shared_file(token, db)
        if not s:
            return Response("<!doctype html><meta charset=utf-8><title>Link expired</title><body style='font-family:system-ui;padding:40px;max-width:520px;margin:auto'><h2>This link has expired</h2><p>The person who shared it can send a new one from TheHealthTracker.</p>", status_code=404, media_type="text/html; charset=utf-8")
        row, data = got
        if raw == "1":
            s.views += 1
            return Response(data, media_type=row.mime, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex", "Content-Disposition": f"inline; filename=\"{(row.name or 'document').replace(chr(34), '')}\""})
        label = _html.escape(s.label or row.name or "Document")
        exp = time.strftime("%d %b %Y, %H:%M", time.localtime(s.expires))
        body = f"<iframe src='/d/{token}?raw=1' title='{label}' style='width:100%;height:80vh;border:0;border-radius:12px;background:#fff'></iframe>" if row.mime == "application/pdf" else f"<img src='/d/{token}?raw=1' alt='{label}' style='max-width:100%;border-radius:12px'>"
        return Response(f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><meta name=robots content=noindex><title>{label} · shared via TheHealthTracker</title>"
                        f"<body style='font-family:Inter,system-ui,sans-serif;background:#f4f5f8;margin:0;padding:20px'><div style='max-width:900px;margin:auto'><p style='color:#646b7e;font-size:13px;margin:0 0 8px'>Shared via TheHealthTracker · link valid until {exp}</p><h2 style='margin:0 0 14px'>{label}</h2>{body}"
                        f"<p style='color:#646b7e;font-size:12px'>This document was shared by its owner for medical care. Please do not forward it.</p></div>", media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-store"})


@app.api_route("/app", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/app/", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/app/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def app_shell(request: Request, rest: str = ""):
    """Deep links: /app/<person>/<profile>/<page> — opaque ids, resolved by the app itself; the shell is the same."""
    return _send(WEB / "index.html", request, "no-cache")


@app.api_route("/s/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def site_assets(rest: str, request: Request):
    p = (SITE / rest).resolve()
    if SITE not in p.parents or not p.is_file():
        raise HTTPException(404)
    return _send(p, request, "public, max-age=86400")


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def static(full_path: str, request: Request):
    if full_path.startswith("api/"):
        raise HTTPException(404)
    rel = full_path or "index.html"
    p = _safe(rel)
    if p.is_dir():
        p = p / "index.html"
    if not p.is_file():  # single-page app: unknown paths fall back to the shell
        if "." in Path(rel).name:
            raise HTTPException(404)
        return _send(SITE / "index.html", request, "no-cache")
    ext = p.suffix.lower()
    headers = {"Vary": "Accept-Encoding"}
    name = p.name
    if name in NO_CACHE:
        headers["Cache-Control"] = "no-cache"
    elif rel.startswith("a/"):  # fingerprinted assets (models, fonts): cache for a year
        headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        headers["Cache-Control"] = "public, max-age=3600"
    path = p
    if ext in COMPRESSIBLE:
        path, enc = _variant(p, request)
        if enc:
            headers["Content-Encoding"] = enc
    # stat_result up front: without it starlette sets the ETag during __call__, i.e. after we would have
    # looked for it, and every conditional request falls through to a full resend.
    return _conditional(request, FileResponse(path, media_type=TYPES.get(ext, "application/octet-stream"),
                                              headers=headers, stat_result=os.stat(path)))

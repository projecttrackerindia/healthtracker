"""TheHealthTracker web server (FastAPI) for Railway.

* Serves the static web app from ./web with pre-compressed (br / gzip) variants, long-lived caching for
  fingerprinted assets and a strict set of security headers.
* Exposes /healthz for Railway's health check and a small versioned JSON API under /api/v1.

Run locally:   uvicorn server:app --reload
On Railway:    the Procfile / railway.json start command uses $PORT.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from sqlalchemy.exc import OperationalError

from api.db import Base, engine, session
from api import admin as admin_api, auth as auth_api, routes as public_api
from api.seed import seed_all

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
ADMIN = ROOT / "admin"
SITE = ROOT / "site"
VERSION = os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev")[:8]
STARTED = time.time()

app = FastAPI(title="TheHealthTracker", version=VERSION, docs_url=None, redoc_url=None, openapi_url="/api/v1/openapi.json")


@app.on_event("startup")
def _init_db():
    try:
        Base.metadata.create_all(engine)
    except OperationalError as e:
        if "already exists" not in str(e):
            raise
    with session() as db:
        seed_all(db)


app.include_router(public_api.r)
app.include_router(auth_api.r)
app.include_router(admin_api.r)

# --------------------------------------------------------------------------------------------------
# Security headers. The app uses inline scripts/styles and a blob: web worker, WebGL and (for SOS)
# geolocation, so the CSP allows exactly that and nothing from other origins.
# --------------------------------------------------------------------------------------------------
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' blob: https://checkout.razorpay.com; "
    "worker-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https://i.ytimg.com; "
    "font-src 'self' data:; "
    "connect-src 'self' blob: data: https://api.razorpay.com https://lumberjack.razorpay.com; "
    "media-src 'self' blob:; "
    "frame-src https://www.youtube-nocookie.com https://www.youtube.com https://api.razorpay.com https://checkout.razorpay.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(self), microphone=(), payment=(self), publickey-credentials-create=(self), publickey-credentials-get=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


@app.middleware("http")
async def headers(request: Request, call_next):
    resp: Response = await call_next(request)
    for k, v in SECURITY.items():
        resp.headers.setdefault(k, v)
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


# --------------------------------------------------------------------------------------------------
# API (Phase 1 starts here; every route is versioned)
# --------------------------------------------------------------------------------------------------
@app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
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
}
COMPRESSIBLE = {".html", ".js", ".css", ".json", ".svg", ".webmanifest", ".txt"}
NO_CACHE = {"index.html", "sw.js", "manifest.webmanifest"}


def _safe(rel: str) -> Path:
    p = (WEB / rel).resolve()
    if WEB not in p.parents and p != WEB:
        raise HTTPException(404)
    return p


@app.api_route("/admin", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/admin/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def admin_page(rest: str = ""):
    return FileResponse(ADMIN / "index.html", media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache", "X-Frame-Options": "DENY"})


def _send(p: Path, request: Request, cache: str):
    ext = p.suffix.lower()
    headers = {"Vary": "Accept-Encoding", "Cache-Control": cache}
    path = p
    if ext in COMPRESSIBLE:
        ae = request.headers.get("accept-encoding", "")
        for enc, suf in (("br", ".br"), ("gzip", ".gz")):
            alt = p.with_name(p.name + suf)
            if enc in ae and alt.is_file():
                path, headers["Content-Encoding"] = alt, enc
                break
    return FileResponse(path, media_type=TYPES.get(ext, "application/octet-stream"), headers=headers)


# landing page (public) at "/", the app at "/app"
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/signin", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/signup", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/reset", methods=["GET", "HEAD"], include_in_schema=False)
def landing(request: Request):
    return _send(SITE / "index.html", request, "no-cache")


@app.api_route("/app", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/app/", methods=["GET", "HEAD"], include_in_schema=False)
def app_shell(request: Request):
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
        ae = request.headers.get("accept-encoding", "")
        for enc, suf in (("br", ".br"), ("gzip", ".gz")):
            alt = p.with_name(p.name + suf)
            if enc in ae and alt.is_file():
                path = alt
                headers["Content-Encoding"] = enc
                break
    return FileResponse(path, media_type=TYPES.get(ext, "application/octet-stream"), headers=headers)

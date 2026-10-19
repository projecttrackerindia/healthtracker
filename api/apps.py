"""App downloads (/api/v1/app/*, /download/android): the Android APK lives in our bucket under releases/.

GitHub Actions uploads `releases/thehealthtracker.apk` + `releases/android.json` (version, size, sha256, built, commit)
after every successful build; an admin can also upload an APK by hand. The site and the app read the metadata and
offer the download; the APK itself is streamed through the server so the bucket stays private.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from . import storage
from .admin import Admin, log
from .admin import me as admin_me
from .db import get_db

r = APIRouter()
KEY_APK = "releases/thehealthtracker.apk"
KEY_META = "releases/android.json"
_CACHE: dict = {"t": 0, "meta": None}


def android_meta(force: bool = False) -> dict | None:
    if not force and time.time() - _CACHE["t"] < 300:
        return _CACHE["meta"]
    meta = None
    s3 = storage._s3()
    if s3:
        try:
            meta = json.loads(s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key=KEY_META)["Body"].read().decode())
        except Exception:
            meta = None
    _CACHE.update(t=time.time(), meta=meta)
    return meta


@r.get("/api/v1/app/android")
def android():
    m = android_meta()
    return {"available": bool(m), "version": (m or {}).get("version", ""), "versionCode": (m or {}).get("versionCode"), "size": (m or {}).get("size"), "sha256": (m or {}).get("sha256", ""),
            "built": (m or {}).get("built"), "commit": (m or {}).get("commit", ""), "url": "/download/android" if m else "", "play": os.getenv("PLAY_STORE_URL", ""),
            "minAndroid": "8.0 (API 26)", "healthConnect": True}


@r.get("/api/v1/app/ios")
def ios():
    return {"available": bool(os.getenv("APPSTORE_URL")), "appstore": os.getenv("APPSTORE_URL", ""), "testflight": os.getenv("TESTFLIGHT_URL", ""),
            "pwa": True, "note": "On iPhone, open thehealthtracker.com/app in Safari → Share → Add to Home Screen for the installable web app today."}


@r.get("/download/android", include_in_schema=False)
def download_android():
    m = android_meta()
    s3 = storage._s3()
    if not m or not s3:
        raise HTTPException(404, "The Android app is not published yet.")
    try:
        obj = s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key=KEY_APK)
    except Exception:
        raise HTTPException(404, "The Android app is not published yet.")
    name = f"TheHealthTracker-{m.get('version', '1.0')}.apk"
    return StreamingResponse(obj["Body"].iter_chunks(1024 * 256), media_type="application/vnd.android.package-archive",
                             headers={"Content-Disposition": f'attachment; filename="{name}"', "Content-Length": str(obj.get("ContentLength", m.get("size", 0))), "Cache-Control": "public, max-age=300"})


@r.put("/api/admin/app/android")
async def upload_android(version: str = Form("1.0"), version_code: int = Form(1), notes: str = Form(""), file: UploadFile = File(...), a: Admin = Depends(admin_me), db=Depends(get_db)):
    """Manual publish: an APK built elsewhere (or the CI artifact) goes live for the site's download button."""
    s3 = storage._s3()
    if not s3:
        raise HTTPException(503, "No bucket configured (S3_BUCKET).")
    data = await file.read()
    if len(data) < 100_000 or data[:2] != b"PK":
        raise HTTPException(415, "That is not an APK.")
    meta = {"version": version[:20], "versionCode": int(version_code), "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "built": int(time.time()), "commit": "", "notes": notes[:400], "by": a.email}
    s3.put_object(Bucket=os.getenv("S3_BUCKET"), Key=KEY_APK, Body=data, ContentType="application/vnd.android.package-archive")
    s3.put_object(Bucket=os.getenv("S3_BUCKET"), Key=KEY_META, Body=json.dumps(meta).encode(), ContentType="application/json")
    android_meta(force=True)
    log(db, a.email, f"app.android.publish {version} {len(data)}B")
    return {"ok": True, **meta}

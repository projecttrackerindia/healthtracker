"""Translations (/api/v1/i18n): the phrase table for Hindi and Telugu.

The repo ships site/i18n/phrases.json (hand-written core + whatever tools/i18n/translate.py produced at build time). A
newer table can be dropped into the bucket at i18n/phrases.json (translate.py --upload) and is served instead, so
translations improve without a release. Cached for an hour.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from . import storage
from .db import get_db

r = APIRouter(prefix="/api/v1")
ROOT = Path(__file__).resolve().parents[1]
_CACHE: dict = {"t": 0, "body": b"", "src": ""}


def load(db: Session | None = None) -> tuple[bytes, str]:
    if time.time() - _CACHE["t"] < 3600 and _CACHE["body"]:
        return _CACHE["body"], _CACHE["src"]
    body, src = b"{}", "none"
    try:
        p = ROOT / "site" / "i18n" / "phrases.json"
        if p.exists():
            body, src = p.read_bytes(), "repo"
    except Exception:
        pass
    try:
        s3 = storage._s3()
        if s3 and os.getenv("S3_BUCKET"):
            data = s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key="i18n/phrases.json")["Body"].read()
            json.loads(data)
            body, src = data, "bucket"
    except Exception:
        pass
    _CACHE.update(t=time.time(), body=body, src=src)
    return body, src


@r.get("/i18n")
def i18n(db: Session = Depends(get_db)):
    body, src = load(db)
    return Response(body, media_type="application/json", headers={"Cache-Control": "public, max-age=3600", "X-I18n-Source": src})

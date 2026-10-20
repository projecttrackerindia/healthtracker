"""Translations (/api/v1/i18n): the phrase table for Hindi and Telugu, and the strings the app finds missing.

Layers, later wins: the repo's site/i18n/phrases.json (hand-written core + the build-time Gemini pass) → the bucket's
i18n/phrases.json (translate.py --upload, so a better table lands without a release) → the `phrases` table, which fills
itself: a phone in Hindi/Telugu mode posts the English strings it painted that had no translation (POST /missing), a
background thread translates them with Gemini in batches, and the next load of /api/v1/i18n carries them. The table has a
version (`__v`) so the app knows when its cached copy is stale.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import storage
from .auth import limit
from .db import SessionLocal, get_db
from .models import Phrase, now

r = APIRouter(prefix="/api/v1")
ROOT = Path(__file__).resolve().parents[1]
_CACHE: dict = {"t": 0, "body": b"", "src": "", "v": 0}
_BG = {"thread": None, "last": 0.0}
MAX_LEN = 200
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
RULES = ("You translate short UI strings for an Indian family health app (TheHealthTracker) from English into Hindi and Telugu. "
         "Register: respectful spoken (आप / మీరు), simple words a parent or grandparent uses; keep medical abbreviations familiar in India as they are (BP, ECG, SpO₂, HbA1c, OTP, SMS, UPI, PIN). "
         "Keep numbers, units, symbols, punctuation, ellipses, arrows and anything in braces or angle brackets exactly. Keep product names (TheHealthTracker, Health Connect, Apple Health, Fitbit, WhatsApp, Aadhaar, DigiLocker, ABHA, NOTTO) in English. "
         "Strings that start or end mid-sentence (lower-case start, trailing ':' or '…', leading '’s') are fragments joined to other text: translate them as fragments. "
         "Return ONLY a JSON object mapping each English string exactly as given to a two-element array [Hindi, Telugu]. No commentary.")
WORDS = re.compile(r"[A-Za-z]{2,}")


def _files() -> tuple[dict, str]:
    table, src = {}, "none"
    try:
        p = ROOT / "site" / "i18n" / "phrases.json"
        if p.exists():
            table, src = json.loads(p.read_text(encoding="utf-8")), "repo"
    except Exception:
        pass
    try:
        s3 = storage._s3()
        if s3 and os.getenv("S3_BUCKET"):
            data = s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key="i18n/phrases.json")["Body"].read()
            table, src = {**table, **json.loads(data)}, "bucket"
    except Exception:
        pass
    return table, src


def load(db: Session | None = None, force: bool = False) -> tuple[bytes, str]:
    if not force and time.time() - _CACHE["t"] < 300 and _CACHE["body"]:
        return _CACHE["body"], _CACHE["src"]
    table, src = _files()
    n = 0
    try:
        s = db or SessionLocal()
        try:
            rows = s.scalars(select(Phrase).where(Phrase.done > 0)).all()
            for p in rows:
                if p.hi and p.te:
                    table[p.en] = [p.hi, p.te]
                    n += 1
            last = s.scalar(select(func.max(Phrase.done))) or 0
        finally:
            if s is not db:
                s.close()
    except Exception as e:
        print("[i18n] db read failed:", str(e)[:120], flush=True)
        last = 0
    table["__v"] = f"{len(table)}.{last}"
    body = json.dumps(table, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _CACHE.update(t=time.time(), body=body, src=src + (f"+db{n}" if n else ""), v=table["__v"])
    return body, _CACHE["src"]


@r.get("/i18n")
def i18n(db: Session = Depends(get_db)):
    body, src = load(db)
    return Response(body, media_type="application/json", headers={"Cache-Control": "no-cache", "X-I18n-Source": src, "ETag": '"' + str(_CACHE["v"]) + '"'})


# ---------------------------------------------------------------- what the phones report as untranslated
class MissingIn(BaseModel):
    items: list[str]


def usable(t: str) -> str:
    """A string worth translating: real words, not a number, code, name-only or a template; trimmed; ≤ MAX_LEN."""
    t = re.sub(r"\s+", " ", (t or "")).strip()
    if not (2 <= len(t) <= MAX_LEN) or not WORDS.search(t) or "{" in t or "<" in t or "${" in t:
        return ""
    if re.fullmatch(r"[\d\W_]*", t) or re.fullmatch(r"[A-Z0-9 _\-./]{2,12}", t):            # codes like "BP", "SPO2", "HD"
        return ""
    if " " not in t and (re.search(r"\d", t) or len(t) <= 2):                               # single tokens like "HbA1c", "SpO₂", "v1.4"
        return ""
    if re.search(r"https?://|@|\.com\b", t):
        return ""
    return t


@r.post("/i18n/missing")
def missing(body: MissingIn, request: Request, db: Session = Depends(get_db)):
    limit(request, "i18n-missing", 60, 3600)
    table = json.loads(load(db)[0].decode("utf-8"))
    added = 0
    seen = set()
    for raw in body.items[:150]:
        t = usable(raw)
        if not t or t in seen or t in table:
            continue
        seen.add(t)
        if db.get(Phrase, t):
            continue
        db.add(Phrase(en=t))
        added += 1
    if added:
        db.commit()
        kick()
    return {"added": added, "pending": int(db.scalar(select(func.count()).select_from(Phrase).where(Phrase.done == 0)) or 0), "translator": bool(os.getenv("GEMINI_API_KEY"))}


# ---------------------------------------------------------------- the background translator
def gemini(batch: list[str]) -> dict:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return {}
    body = {"system_instruction": {"parts": [{"text": RULES}]}, "contents": [{"parts": [{"text": json.dumps(batch, ensure_ascii=False)}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}}
    for m in dict.fromkeys([MODEL, "gemini-flash-latest"]):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                j = json.loads(resp.read().decode())
            return json.loads(j["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:  # noqa: BLE001
            print("[i18n] gemini failed:", m, str(e)[:160], flush=True)
    return {}


def translate_pending(db: Session, batch_size: int = 50, max_batches: int = 20) -> int:
    """Translate up to max_batches × batch_size pending rows. Returns how many landed."""
    done = 0
    for _ in range(max_batches):
        rows = db.scalars(select(Phrase).where(Phrase.done == 0, Phrase.tries < 3).order_by(Phrase.created).limit(batch_size)).all()
        if not rows:
            break
        got = gemini([p.en for p in rows])
        for p in rows:
            v = got.get(p.en)
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) and x.strip() for x in v):
                p.hi, p.te, p.done = v[0].strip()[:400], v[1].strip()[:400], now()
                done += 1
            else:
                p.tries += 1
        db.commit()
        if not got:
            break
    if done:
        _CACHE["t"] = 0     # next GET rebuilds the table
    return done


def _worker():
    time.sleep(3)
    try:
        s = SessionLocal()
        try:
            n = translate_pending(s)
            if n:
                print(f"[i18n] translated {n} phrases", flush=True)
        finally:
            s.close()
    except Exception as e:
        print("[i18n] worker failed:", str(e)[:160], flush=True)
    _BG["thread"] = None


def kick() -> None:
    """Start the translator once per burst (the thread drains everything pending, then exits)."""
    if not os.getenv("GEMINI_API_KEY") or os.getenv("I18N_AUTO", "1") != "1":
        return
    t = _BG.get("thread")
    if t and t.is_alive():
        return
    _BG["thread"] = threading.Thread(target=_worker, daemon=True, name="i18n")
    _BG["thread"].start()

"""Translate the app's P('…') phrases to Hindi and Telugu with Gemini, keeping the hand-written core.

    GEMINI_API_KEY=… python tools/i18n/translate.py            # writes site/i18n/phrases.json
    … --upload                                                  # also puts it in the bucket (S3_* env), served by /api/v1/i18n at once

Rules the model is given: plain, respectful spoken register (आप / మీరు), medical terms kept simple with the English in
brackets where a parent would know the English word (BP, ECG, HbA1c), numbers/units/placeholders unchanged, brand and
product names unchanged, same length order as the English. Output is reviewed by a doctor before the "awaiting review"
note comes off; until then the app says so.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "i18n"))
from core import CORE  # noqa: E402

OUT = ROOT / "site" / "i18n" / "phrases.json"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
from core import RULES  # noqa: E402


def phrases() -> list[str]:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    seen, out = set(), []
    for p in re.findall(r"P\('((?:[^'\\]|\\.)*)'\)", html):
        p = p.replace("\\'", "'")
        if p in seen or p in CORE or re.fullmatch(r"[\d\W_]*", p) or len(p) > 400:
            continue
        seen.add(p)
        out.append(p)
    return out


def gemini(batch: list[str]) -> dict:
    key = os.environ["GEMINI_API_KEY"]
    body = {"system_instruction": {"parts": [{"text": RULES}]}, "contents": [{"parts": [{"text": json.dumps(batch, ensure_ascii=False)}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.loads(r.read().decode())
            text = j["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as e:  # noqa: BLE001
            print("  retry", attempt + 1, str(e)[:120], flush=True)
            time.sleep(3 * (attempt + 1))
    return {}


def main() -> None:
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    todo = [p for p in phrases() if p not in existing or len(existing[p]) != 2]
    print(f"{len(todo)} phrases to translate ({len(existing)} already, {len(CORE)} hand-written)", flush=True)
    for i in range(0, len(todo), 60):
        batch = todo[i:i + 60]
        got = gemini(batch)
        ok = 0
        for p in batch:
            v = got.get(p)
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) and x.strip() for x in v):
                existing[p] = [v[0].strip(), v[1].strip()]
                ok += 1
        print(f"  {i + len(batch)}/{len(todo)} · {ok}/{len(batch)} ok", flush=True)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({**existing, **CORE}, ensure_ascii=False, indent=0), encoding="utf-8")
    merged = {**existing, **CORE}
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=0), encoding="utf-8")
    print("wrote", OUT, len(merged), "phrases")
    if "--upload" in sys.argv:
        import boto3
        kw = {"region_name": os.getenv("S3_REGION") or "auto", "aws_access_key_id": os.environ["S3_ACCESS_KEY"], "aws_secret_access_key": os.environ["S3_SECRET_KEY"]}
        if os.getenv("S3_ENDPOINT"):
            kw["endpoint_url"] = os.environ["S3_ENDPOINT"]
        boto3.client("s3", **kw).put_object(Bucket=os.environ["S3_BUCKET"], Key="i18n/phrases.json", Body=OUT.read_bytes(), ContentType="application/json")
        print("uploaded to the bucket: live now at /api/v1/i18n")


if __name__ == "__main__":
    main()

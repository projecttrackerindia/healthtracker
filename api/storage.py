"""Encrypted file storage for a family's documents (reports, prescriptions, card scans).

Bytes are encrypted with AES-GCM (same DATA_KEY as the household state) before they leave the server process, then kept in
an S3-compatible bucket when S3_BUCKET is set (Cloudflare R2, AWS S3 Mumbai, Backblaze B2...) and otherwise in the
database table `files` (fine for a small launch; move to a bucket before files grow past a few GB).
"""
from __future__ import annotations

import os
import secrets

from .family import _key, open_with_keys

MAX_FILE = 15 * 1024 * 1024
PREFIX = os.getenv("S3_PREFIX", "tht/")


_CLIENT: dict = {}


def _s3():
    """Cached: botocore reads its service model off disk on every client build, which is tens of milliseconds
    of file I/O we were paying on every upload and download."""
    if not os.getenv("S3_BUCKET"):
        return None
    if _CLIENT.get("c") is not None:
        return _CLIENT["c"]
    import boto3  # imported lazily: only needed when a bucket is configured

    from botocore.config import Config

    # "when_required": recent boto3 adds CRC checksum headers that Google Cloud Storage's S3 interop (and some other S3 clones) reject
    cfg = {"s3": {"addressing_style": os.getenv("S3_ADDRESSING", "auto")}}
    # an upload with no timeout can hold a worker until the socket gives up; these are generous but finite
    cfg["connect_timeout"] = int(os.getenv("S3_CONNECT_TIMEOUT", "5"))
    cfg["read_timeout"] = int(os.getenv("S3_READ_TIMEOUT", "30"))
    cfg["retries"] = {"max_attempts": 2, "mode": "standard"}
    try:
        conf = Config(request_checksum_calculation="when_required", response_checksum_validation="when_required", **cfg)
    except TypeError:  # older botocore without those options
        conf = Config(**cfg)
    kw = {"region_name": os.getenv("S3_REGION", "auto"), "config": conf}
    if os.getenv("S3_ENDPOINT"):
        kw["endpoint_url"] = os.getenv("S3_ENDPOINT")
    if os.getenv("S3_ACCESS_KEY"):
        kw["aws_access_key_id"] = os.getenv("S3_ACCESS_KEY")
        kw["aws_secret_access_key"] = os.getenv("S3_SECRET_KEY")
    _CLIENT["c"] = boto3.client("s3", **kw)
    return _CLIENT["c"]


def backend() -> str:
    return "s3" if os.getenv("S3_BUCKET") else "db"


def seal(data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    return b"f1" + nonce + AESGCM(_key()).encrypt(nonce, data, b"tht-file-v1")


def unseal(blob: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if blob[:2] != b"f1":
        raise ValueError("unknown file blob")
    return open_with_keys(blob[14:], blob[2:14], b"tht-file-v1")


def put(db, household_id: str, file_id: str, data: bytes, mime: str, name: str, by: str) -> int:
    from .models import StoredFile, now

    blob = seal(data)
    key = f"{PREFIX}{household_id}/{file_id}"
    s3 = _s3()
    if s3:
        s3.put_object(Bucket=os.getenv("S3_BUCKET"), Key=key, Body=blob, ContentType="application/octet-stream")
    row = db.get(StoredFile, (household_id, file_id))
    if row:
        row.size, row.mime, row.name, row.updated, row.blob = len(data), mime, name, now(), (None if s3 else blob)
    else:
        db.add(StoredFile(household_id=household_id, file_id=file_id, size=len(data), mime=mime, name=name, by_user=by, blob=None if s3 else blob, where="s3" if s3 else "db"))
    return len(data)


def get(db, household_id: str, file_id: str):
    from .models import StoredFile

    row = db.get(StoredFile, (household_id, file_id))
    if not row:
        return None
    if row.where == "s3":
        s3 = _s3()
        if not s3:
            raise RuntimeError("file is in the bucket but S3 is not configured")
        blob = s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key=f"{PREFIX}{household_id}/{file_id}")["Body"].read()
    else:
        blob = row.blob
    return row, unseal(blob)


def delete(db, household_id: str, file_id: str) -> bool:
    from .models import StoredFile

    row = db.get(StoredFile, (household_id, file_id))
    if not row:
        return False
    if row.where == "s3":
        s3 = _s3()
        if s3:
            try:
                s3.delete_object(Bucket=os.getenv("S3_BUCKET"), Key=f"{PREFIX}{household_id}/{file_id}")
            except Exception as e:
                print("[storage] s3 delete failed:", str(e)[:200], flush=True)
    db.delete(row)
    return True


def delete_household(db, household_id: str) -> int:
    from sqlalchemy import select

    from .models import StoredFile

    rows = db.scalars(select(StoredFile).where(StoredFile.household_id == household_id)).all()
    for r in rows:
        delete(db, household_id, r.file_id)
    return len(rows)

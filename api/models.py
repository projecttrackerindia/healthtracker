"""Tables. JSON columns hold small lists/dicts (items, timelines, features) so the schema stays short."""
from __future__ import annotations

import time
import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> int:
    return int(time.time())


def new_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex[:12]


class Household(Base):
    """One TheHealthTracker install (a family on a device). Identified by an anonymous key the app generates; no account yet."""

    __tablename__ = "households"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("h"))
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(24), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    plan: Mapped[str] = mapped_column(String(24), default="free")
    plan_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    members: Mapped[int] = mapped_column(Integer, default=1)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    backup_at: Mapped[int | None] = mapped_column(Integer, nullable=True)      # last emailed copy of the record
    backup_to: Mapped[str] = mapped_column(String(200), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    last_seen: Mapped[int] = mapped_column(Integer, default=now)
    orders: Mapped[list["Order"]] = relationship(back_populates="household")


class Store(Base):
    """A partner: pharmacy, diagnostic lab or hospital. Onboarded and verified in the admin panel."""

    __tablename__ = "stores"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("s"))
    kind: Mapped[str] = mapped_column(String(16), index=True)  # pharmacy | lab | hospital
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str] = mapped_column(String(80), default="")
    address: Mapped[str] = mapped_column(String(240), default="")
    area: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), index=True)
    pin: Mapped[str] = mapped_column(String(12), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    phone: Mapped[str] = mapped_column(String(24), default="")
    hours: Mapped[str] = mapped_column(String(80), default="8 am – 10 pm")
    open_24h: Mapped[bool] = mapped_column(Boolean, default=False)
    licence: Mapped[str] = mapped_column(String(64), default="")  # drug licence / NABL number (admin-entered)
    gstin: Mapped[str] = mapped_column(String(20), default="")    # printed on receipts when present
    gst_pct: Mapped[int] = mapped_column(Integer, default=0)      # GST included in this seller's prices (0 = not shown separately)
    rating: Mapped[float] = mapped_column(Float, default=4.3)
    rating_n: Mapped[int] = mapped_column(Integer, default=0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0)  # off MRP on medicines
    delivery: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_fee: Mapped[int] = mapped_column(Integer, default=30)
    free_above: Mapped[int] = mapped_column(Integer, default=499)
    eta_min: Mapped[int] = mapped_column(Integer, default=60)  # typical delivery / report time in minutes
    home_collection: Mapped[bool] = mapped_column(Boolean, default=False)  # labs
    collection_fee: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_email: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    items: Mapped[list["StoreItem"]] = relationship(back_populates="store", cascade="all, delete-orphan")
    tests: Mapped[list["LabTest"]] = relationship(back_populates="store", cascade="all, delete-orphan")


Index("ix_stores_geo", Store.kind, Store.lat, Store.lng)


class StoreItem(Base):
    """A medicine a pharmacy stocks, with its own price (MRP minus the store discount, or a specific price)."""

    __tablename__ = "store_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(40), index=True)  # catalogue id (para500 …)
    name: Mapped[str] = mapped_column(String(120))
    mrp: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=20)
    store: Mapped[Store] = relationship(back_populates="items")


class LabTest(Base):
    __tablename__ = "lab_tests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)  # hb, hba1c, lipid …
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[int] = mapped_column(Integer)
    tat_hours: Mapped[int] = mapped_column(Integer, default=24)
    fasting: Mapped[bool] = mapped_column(Boolean, default=False)
    store: Mapped[Store] = relationship(back_populates="tests")


class Order(Base):
    """A medicine order or a lab booking. Status moves through a timeline the store (or the demo clock) advances."""

    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("o").upper()[:10])
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="medicine")  # medicine | lab
    items: Mapped[list] = mapped_column(JSON, default=list)  # [{sku,name,qty,price,rx}] or [{code,name,price}]
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    fee: Mapped[int] = mapped_column(Integer, default=0)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    address: Mapped[str] = mapped_column(String(240), default="")
    member: Mapped[str] = mapped_column(String(80), default="")  # first name only, as the family typed it
    rx_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    member_id: Mapped[str | None] = mapped_column(String(32), nullable=True)   # which family profile the order is for
    rx_files: Mapped[list | None] = mapped_column(JSON, nullable=True)         # prescription file ids the family chose to share
    addr: Mapped[dict | None] = mapped_column(JSON, nullable=True)             # structured delivery / collection address {label,name,phone,line1,line2,landmark,area,city,state,pin,lat,lng}
    slot: Mapped[str] = mapped_column(String(40), default="")  # lab home-collection slot
    status: Mapped[str] = mapped_column(String(24), default="placed", index=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list)  # [{s,t}]
    eta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment: Mapped[str] = mapped_column(String(24), default="cod")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_tags: Mapped[list] = mapped_column(JSON, default=list)
    rating_note: Mapped[str] = mapped_column(String(400), default="")
    created: Mapped[int] = mapped_column(Integer, default=now, index=True)
    household: Mapped[Household] = relationship(back_populates="orders")
    store: Mapped[Store] = relationship()


class Plan(Base):
    __tablename__ = "plans"
    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    price_month: Mapped[int] = mapped_column(Integer, default=0)  # INR
    price_year: Mapped[int] = mapped_column(Integer, default=0)
    members: Mapped[int] = mapped_column(Integer, default=5)
    features: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("sub"))
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    plan: Mapped[str] = mapped_column(String(24))
    period: Mapped[str] = mapped_column(String(8), default="month")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")  # pending | active | cancelled | failed
    provider: Mapped[str] = mapped_column(String(16), default="demo")  # demo | razorpay
    provider_ref: Mapped[str] = mapped_column(String(80), default="")
    started: Mapped[int] = mapped_column(Integer, default=now)
    renews: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoice_no: Mapped[str] = mapped_column(String(32), default="")


class Seasonal(Base):
    """Seasonal disease advisories shown on Home by month and region."""

    __tablename__ = "seasonal"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("sz"))
    region: Mapped[str] = mapped_column(String(40), default="IN")  # IN or a state code (TS, KA …)
    months: Mapped[list] = mapped_column(JSON, default=list)  # [6,7,8,9]
    disease: Mapped[str] = mapped_column(String(80))
    emoji: Mapped[str] = mapped_column(String(8), default="🦟")
    risk: Mapped[str] = mapped_column(String(12), default="medium")  # low | medium | high
    summary: Mapped[str] = mapped_column(String(300), default="")
    symptoms: Mapped[list] = mapped_column(JSON, default=list)
    prevention: Mapped[list] = mapped_column(JSON, default=list)
    see_doctor: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(120), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class Video(Base):
    """First-aid teaching videos from official organisations, embedded from YouTube (never downloaded)."""

    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("v"))
    topic: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(String(80))
    yt: Mapped[str] = mapped_column(String(16))
    lang: Mapped[str] = mapped_column(String(8), default="en")
    minutes: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(240), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    pw_hash: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(16), default="owner")  # owner | ops | content
    created: Mapped[int] = mapped_column(Integer, default=now)
    last_login: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)
    who: Mapped[str] = mapped_column(String(120), default="")
    what: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text, default="")


class AiCache(Base):
    """A day's insight for one person, keyed by the records it was made from. Expires after two days."""

    __tablename__ = "ai_cache"
    key: Mapped[str] = mapped_column(String(96), primary_key=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    t: Mapped[int] = mapped_column(Integer, default=now)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class AiJob(Base):
    """What was analysed (never the document itself): kind, source engine, timing, token cost. For the admin dashboard."""

    __tablename__ = "ai_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)
    household_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    kind: Mapped[str] = mapped_column(String(16))
    engine: Mapped[str] = mapped_column(String(24))
    ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    findings: Mapped[int] = mapped_column(Integer, default=0)
    tin: Mapped[int] = mapped_column(Integer, default=0)   # input tokens
    tout: Mapped[int] = mapped_column(Integer, default=0)  # output tokens


class PerfSample(Base):
    """Anonymous page-speed beacons from the app (no identity, no content): how fast it opens on real phones."""

    __tablename__ = "perf_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)
    kind: Mapped[str] = mapped_column(String(12), default="web")      # web | android | ios
    phone: Mapped[bool] = mapped_column(Boolean, default=False)
    ttfb: Mapped[int] = mapped_column(Integer, default=0)
    dcl: Mapped[int] = mapped_column(Integer, default=0)      # DOMContentLoaded (ms)
    load: Mapped[int] = mapped_column(Integer, default=0)     # window load (ms)
    ready: Mapped[int] = mapped_column(Integer, default=0)    # app booted (ms)
    lcp: Mapped[int] = mapped_column(Integer, default=0)
    cls: Mapped[int] = mapped_column(Integer, default=0)      # ×1000
    conn: Mapped[str] = mapped_column(String(12), default="")  # 4g / 3g / wifi hint
    sw: Mapped[bool] = mapped_column(Boolean, default=False)   # served by the service worker


# ---------------------------------------------------------------------------------------------------------------------
# Accounts: users, passkeys (WebAuthn), one-time codes, sessions and short-lived auth flows
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("u"))
    email: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)  # E.164, e.g. +919876543210
    name: Mapped[str] = mapped_column(String(80), default="")
    pw_hash: Mapped[str] = mapped_column(String(200), default="")
    pw_changed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    two_step: Mapped[bool] = mapped_column(Boolean, default=False)  # password sign-in also needs a one-time code
    webauthn_id: Mapped[str] = mapped_column(String(64), default=lambda: uuid.uuid4().hex)  # opaque user handle
    household_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    member_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # which family profile is 'me' for this account
    name_changed: Mapped[int | None] = mapped_column(Integer, nullable=True)  # the account name (as on Aadhaar) changes at most once a week
    role: Mapped[str] = mapped_column(String(12), default="member")  # admin | member | caregiver — what this sign-in may change in the family record
    aadhaar_verified: Mapped[int | None] = mapped_column(Integer, nullable=True)  # when identity was confirmed through DigiLocker (Aadhaar e-KYC)
    aadhaar_last4: Mapped[str] = mapped_column(String(4), default="")
    aadhaar_dob: Mapped[str] = mapped_column(String(10), default="")  # DD-MM-YYYY as printed on Aadhaar
    ref_code: Mapped[str] = mapped_column(String(12), default="", index=True)   # this person's invite code (THT-XXXXXX)
    referred_by: Mapped[str] = mapped_column(String(32), default="")           # user id of whoever invited them
    ref_rewarded: Mapped[int] = mapped_column(Integer, default=0)              # when the inviter's reward was granted
    failed: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[int] = mapped_column(Integer, default=now)
    last_login: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passkeys: Mapped[list["Passkey"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Passkey(Base):
    __tablename__ = "passkeys"
    id: Mapped[str] = mapped_column(String(400), primary_key=True)  # credential id, base64url
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    public_key: Mapped[str] = mapped_column(Text)  # COSE key, base64url
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list] = mapped_column(JSON, default=list)
    name: Mapped[str] = mapped_column(String(80), default="Passkey")
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[int] = mapped_column(Integer, default=now)
    last_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user: Mapped[User] = relationship(back_populates="passkeys")


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("c"))
    target: Mapped[str] = mapped_column(String(160), index=True)  # email or E.164 phone
    purpose: Mapped[str] = mapped_column(String(16))  # signin | signup | reset | verify | step
    code_hash: Mapped[str] = mapped_column(String(80))
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str] = mapped_column(String(64), default="")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)  # sha256 of the cookie token
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    last_seen: Mapped[int] = mapped_column(Integer, default=now)
    method: Mapped[str] = mapped_column(String(16), default="")  # passkey | password | otp
    ua: Mapped[str] = mapped_column(String(200), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")


class AuthFlow(Base):
    """Server-side state for a multi-step sign-in (WebAuthn challenge, pending two-step)."""

    __tablename__ = "auth_flows"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # reg | auth | step
    challenge: Mapped[str] = mapped_column(String(200), default="")
    user_id: Mapped[str] = mapped_column(String(32), default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    expires: Mapped[int] = mapped_column(Integer)


class HouseholdStateHistory(Base):
    """Every previous version of a family's record, kept for 30 days, so a bad sync from one device can always be undone."""

    __tablename__ = "household_state_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    sect: Mapped[dict] = mapped_column(JSON, default=dict)
    size: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[str] = mapped_column(String(32), default="")
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)


class HouseholdState(Base):
    """The family's app data (profiles, results, medicines, cards...) as one encrypted JSON blob per household, so every
    signed-in family member sees the same records on every device. Files (photos, PDFs) are not included."""

    __tablename__ = "household_state"
    household_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    blob: Mapped[bytes] = mapped_column(LargeBinary)          # AES-GCM(zlib(JSON))
    sect: Mapped[dict] = mapped_column(JSON, default=dict)   # section -> last-changed timestamp (ms), for merging
    size: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=now, onupdate=now)
    updated_by: Mapped[str] = mapped_column(String(32), default="")


class Invite(Base):
    """A family member's invitation to create their own account for an existing profile."""

    __tablename__ = "invites"
    token: Mapped[str] = mapped_column(String(48), primary_key=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(80), default="")
    contact: Mapped[str] = mapped_column(String(160), default="")
    by_user: Mapped[str] = mapped_column(String(32), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    used_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(12), default="member")  # what the joining sign-in becomes: member | caregiver
    used: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StoredFile(Base):
    """A family's document (report, prescription, card scan), encrypted. Bytes live in the bucket or, without one, here."""

    __tablename__ = "files"
    household_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    file_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String(80), default="application/octet-stream")
    name: Mapped[str] = mapped_column(String(160), default="")
    where: Mapped[str] = mapped_column(String(8), default="db")      # db | s3
    blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    by_user: Mapped[str] = mapped_column(String(32), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class ShareLink(Base):
    """Time-limited link to one document, for a doctor who does not use the app."""

    __tablename__ = "share_links"
    token: Mapped[str] = mapped_column(String(48), primary_key=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    file_id: Mapped[str] = mapped_column(String(48))
    label: Mapped[str] = mapped_column(String(160), default="")
    by_user: Mapped[str] = mapped_column(String(32), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    views: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class PushSub(Base):
    """A browser's Web Push subscription for one account."""

    __tablename__ = "push_subs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ps"))
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    sub: Mapped[dict] = mapped_column(JSON)
    ua: Mapped[str] = mapped_column(String(200), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    failures: Mapped[int] = mapped_column(Integer, default=0)


class RtcPeer(Base):
    """Who is on a call and which container their socket is attached to.

    A WebSocket belongs to one process, so the signalling rooms could never be shared between containers —
    which is the other half of why the service ran with --max-instances 1. Presence lives here instead of in
    one process's memory, and the relay table below carries messages between containers."""

    __tablename__ = "rtc_peers"
    aid: Mapped[str] = mapped_column(String(40), primary_key=True)
    role: Mapped[str] = mapped_column(String(10), primary_key=True)
    instance: Mapped[str] = mapped_column(String(64), default="")
    seen: Mapped[int] = mapped_column(Integer, default=now, index=True)


class RtcRelay(Base):
    """Signalling messages for a peer attached to a different container.

    Signalling is a few dozen small messages while a call is set up; once the peers are connected, WebRTC is
    direct and this goes quiet. That volume does not justify Redis."""

    __tablename__ = "rtc_relay"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aid: Mapped[str] = mapped_column(String(40), index=True)
    to_role: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[int] = mapped_column(Integer, default=now, index=True)


class TaskLock(Base):
    """A lease, so that when several containers are running only one of them performs a scheduled tick.

    Acquiring is one conditional UPDATE: a row is taken only if nobody holds it or the holder's lease has
    expired. That makes it safe without a second service to run — no Redis, no leader election — and a holder
    that dies simply loses the lease when it runs out rather than blocking the task forever."""

    __tablename__ = "task_locks"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    holder: Mapped[str] = mapped_column(String(64), default="")
    until: Mapped[int] = mapped_column(Integer, default=0, index=True)
    ran_at: Mapped[int] = mapped_column(Integer, default=0)


class ReminderSent(Base):
    """Which reminder went out already (one per member, day, slot, kind)."""

    __tablename__ = "reminders_sent"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)   # range-deleted every tick; without this it is a seq scan per minute


class ClientError(Base):
    """JavaScript errors reported by the app, so problems are seen before people complain."""

    __tablename__ = "client_errors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ce"))
    t: Mapped[int] = mapped_column(Integer, default=now)
    message: Mapped[str] = mapped_column(String(400), default="")
    stack: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[str] = mapped_column(String(80), default="")
    ua: Mapped[str] = mapped_column(String(200), default="")
    version: Mapped[str] = mapped_column(String(16), default="")
    count: Mapped[int] = mapped_column(Integer, default=1)


class Setting(Base):
    """Small admin-editable values (clinical reviewer, announcements)."""

    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(48), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated: Mapped[int] = mapped_column(Integer, default=now, onupdate=now)


# ---- partner network: the lab / pharmacy / hospital side -----------------------------------------------------------------
class PartnerUser(Base):
    """A person at a partner store who signs in to the partner portal. Created by an admin; the store must be verified."""

    __tablename__ = "partner_users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("pu"))
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    pw_hash: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(16), default="staff")  # owner | staff | doctor
    reg_no: Mapped[str] = mapped_column(String(40), default="")     # doctors: NMC / state medical council registration
    specialty: Mapped[str] = mapped_column(String(60), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)   # doctors: registration checked by an admin
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change: Mapped[bool] = mapped_column(Boolean, default=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    last_login: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Appointment(Base):
    """A visit requested at a partner hospital or clinic; the partner confirms a slot, reschedules or declines."""

    __tablename__ = "appointments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ap"))
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), default="")
    member_name: Mapped[str] = mapped_column(String(80), default="")
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="visit")  # visit | video
    date: Mapped[str] = mapped_column(String(10), default="")
    time: Mapped[str] = mapped_column(String(8), default="")
    why: Mapped[str] = mapped_column(String(160), default="")
    doctor: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(16), default="requested", index=True)  # requested | confirmed | rescheduled | declined | done | cancelled
    slot_date: Mapped[str] = mapped_column(String(10), default="")
    slot_time: Mapped[str] = mapped_column(String(8), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    transcript: Mapped[list | None] = mapped_column(JSON, nullable=True)   # [{who, t, text}] from the video consult
    rx: Mapped[dict | None] = mapped_column(JSON, nullable=True)           # {items:[{name,strength,form,frequency,duration,instructions,rx}], advice, doctor, t}
    summary: Mapped[str] = mapped_column(Text, default="")                 # AI visit summary, for discussion with the doctor
    call_started: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_ended: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class Notice(Base):
    """Something that happened on the server side that the family should see: order status, report ready, visit confirmed, message."""

    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), default="")
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(400), default="")
    ref: Mapped[dict] = mapped_column(JSON, default=dict)
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    """A message between a family and a partner store (about an order, a booking or a visit). Attachments are file ids."""

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    sender: Mapped[str] = mapped_column(String(8))  # family | partner
    sender_name: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(String(2000), default="")
    file_id: Mapped[str] = mapped_column(String(48), default="")
    t: Mapped[int] = mapped_column(Integer, default=now, index=True)
    read_family: Mapped[bool] = mapped_column(Boolean, default=False)
    read_partner: Mapped[bool] = mapped_column(Boolean, default=False)


class MedicalId(Base):
    """A member's lock-screen Medical ID: the few facts a first responder needs (blood group, allergies, conditions, medicines,
    emergency contacts), published at /m/<token> and as a QR code. The family turns it on per person and can rotate or
    switch it off any time; the payload is sealed with the data key at rest and only served while enabled."""

    __tablename__ = "medical_ids"
    token: Mapped[str] = mapped_column(String(40), primary_key=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    last_view: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class PartnerApplication(Base):
    """A lab, pharmacy or hospital asking to join from /partner → Apply. An admin reviews it; approving creates the store and
    the owner's sign-in."""

    __tablename__ = "partner_applications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("pa"))
    kind: Mapped[str] = mapped_column(String(16))  # pharmacy | lab | hospital
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(80), default="")
    email: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(24), default="")
    address: Mapped[str] = mapped_column(String(240), default="")
    area: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    pin: Mapped[str] = mapped_column(String(12), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    licence: Mapped[str] = mapped_column(String(64), default="")   # drug licence / NABL / clinical establishment registration
    gstin: Mapped[str] = mapped_column(String(20), default="")
    services: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="new", index=True)  # new | approved | declined
    store_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    decided_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip: Mapped[str] = mapped_column(String(48), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)


class Payment(Base):
    """A UPI payment the family makes by scanning our QR (plan upgrade or an order), confirmed by an admin against the bank
    statement. Razorpay payments go through the subscribe/webhook path instead; this is the manual UPI route."""

    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("pay"))
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), default="")
    kind: Mapped[str] = mapped_column(String(12))                       # plan | order
    ref: Mapped[str] = mapped_column(String(48), default="")            # "family:year" or an order id
    amount: Mapped[int] = mapped_column(Integer, default=0)             # INR
    account: Mapped[str] = mapped_column(String(16), default="")        # which UPI account was shown
    vpa: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(40), default="")           # the reference the payer types / that is in the QR
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)  # pending | claimed | confirmed | rejected | expired
    utr: Mapped[str] = mapped_column(String(40), default="")
    payer: Mapped[str] = mapped_column(String(80), default="")
    claimed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(120), default="")
    decided_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_note: Mapped[str] = mapped_column(String(300), default="")
    created: Mapped[int] = mapped_column(Integer, default=now, index=True)


class DeviceLink(Base):
    """A cloud wearable account (Fitbit today) linked to one family profile; tokens are sealed with the data key."""

    __tablename__ = "device_links"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("dl"))
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), default="")
    user_id: Mapped[str] = mapped_column(String(32), default="")
    provider: Mapped[str] = mapped_column(String(16), default="fitbit")
    external_id: Mapped[str] = mapped_column(String(64), default="")
    blob: Mapped[bytes] = mapped_column(LargeBinary)              # sealed {access, refresh, expires, scope}
    last_sync: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[int] = mapped_column(Integer, default=now)


class ShopProduct(Base):
    """A TheHealthTracker package or merchandise item (the hospital-bag package first). Price, MRP and stock live on the
    shop store's StoreItem with the same sku, so orders flow through the normal order machinery."""

    __tablename__ = "shop_products"
    sku: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tagline: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    includes: Mapped[list] = mapped_column(JSON, default=list)      # [{group, name, qty}]
    sizes: Mapped[list] = mapped_column(JSON, default=list)         # e.g. ["S","M","L","XL"] for the mother's wear
    size_note: Mapped[str] = mapped_column(String(160), default="")
    image_key: Mapped[str] = mapped_column(String(80), default="")  # bucket key shop/<sku>.jpg
    badge: Mapped[str] = mapped_column(String(40), default="")
    ships_in: Mapped[str] = mapped_column(String(40), default="3–5 days")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class Donor(Base):
    """A family member who opted in to be called for blood: group, where they are, when they last gave.
    Registered from Medical ID with explicit consent; hospitals see name, group and phone only after they respond."""

    __tablename__ = "donors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("dn"))
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    group: Mapped[str] = mapped_column(String(4), index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str] = mapped_column(String(80), default="")
    last_donation: Mapped[str] = mapped_column(String(10), default="")
    sex: Mapped[str] = mapped_column(String(8), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_t: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)
    donations: Mapped[int] = mapped_column(Integer, default=0)


class BloodRequest(Base):
    """Raised only by verified hospitals / blood banks (partner portal). Matching donors nearby are notified."""

    __tablename__ = "blood_requests"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("br"))
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(32), default="")
    patient: Mapped[str] = mapped_column(String(40), default="")     # first name or "patient"
    group: Mapped[str] = mapped_column(String(4), index=True)
    component: Mapped[str] = mapped_column(String(12), default="whole")  # whole | platelets | plasma | rbc
    units: Mapped[int] = mapped_column(Integer, default=1)
    urgency: Mapped[str] = mapped_column(String(10), default="24h")   # now | 24h | 72h
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    hospital: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(240), default="")
    ward: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(String(300), default="")
    radius_km: Mapped[int] = mapped_column(Integer, default=25)
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | fulfilled | closed | expired
    notified: Mapped[int] = mapped_column(Integer, default=0)
    expires: Mapped[int] = mapped_column(Integer)
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)


class DonorResponse(Base):
    """A donor's answer to a request and, once accepted, their live position on the way."""

    __tablename__ = "donor_responses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("dr"))
    request_id: Mapped[str] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True)
    donor_id: Mapped[str] = mapped_column(String(32), index=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(12), default="offered")  # offered | accepted | declined | on_way | arrived | donated | withdrawn
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    eta_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loc_t: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)

class SosAlert(Base):
    """One SOS press: who, where (updated while the alert is open), what was sent, and a public token for the live page."""

    __tablename__ = "sos_alerts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("sos"))
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    token: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    member_id: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)        # medical summary + contacts (names, channels), phone of the person
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    acc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trail: Mapped[list] = mapped_column(JSON, default=list)       # [[t, lat, lng]] last 50 positions
    sent: Mapped[list] = mapped_column(JSON, default=list)        # [{n, channel, ok}]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created: Mapped[int] = mapped_column(Integer, default=now)
    updated: Mapped[int] = mapped_column(Integer, default=now)
    ended: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SharedSummary(Base):
    """A time-limited link to a person's doctor summary (one page: allergies, medicines, results, readings, contacts), sealed at rest."""

    __tablename__ = "shared_summaries"
    token: Mapped[str] = mapped_column(String(48), primary_key=True)
    household_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    label: Mapped[str] = mapped_column(String(160), default="")
    blob: Mapped[bytes] = mapped_column(LargeBinary)            # sealed HTML
    by_user: Mapped[str] = mapped_column(String(32), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    views: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Phrase(Base):
    """A UI string the app met on a phone in Hindi/Telugu mode that the phrase table did not cover. Translated in the background
    (Gemini), then served by /api/v1/i18n to every device — so the app's coverage grows on its own instead of waiting for a release."""

    __tablename__ = "phrases"
    en: Mapped[str] = mapped_column(String(200), primary_key=True)
    hi: Mapped[str] = mapped_column(String(400), default="")
    te: Mapped[str] = mapped_column(String(400), default="")
    src: Mapped[str] = mapped_column(String(12), default="auto")      # auto (model) | reviewed (a doctor / translator signed off)
    created: Mapped[int] = mapped_column(Integer, default=now)
    done: Mapped[int] = mapped_column(Integer, default=0)             # when the translation landed (0 = still pending)
    tries: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_phrases_pending", "done", "tries", "created"),)   # the pending-work scan on every /i18n call

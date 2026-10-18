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


class ReminderSent(Base):
    """Which reminder went out already (one per member, day, slot, kind)."""

    __tablename__ = "reminders_sent"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    t: Mapped[int] = mapped_column(Integer, default=now)


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

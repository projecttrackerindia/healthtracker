"""The admin console's three everyday views: Today (what needs a person), the live orders board, and search.

Everything here is read-only and computed from the tables the rest of the app already keeps, so nothing in this
file can drift out of step with an order or a partner. Families appear only as a masked first name and area:
the console is for running the network, not for reading anyone's health."""
from __future__ import annotations

import os
import re
import time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .admin import me as admin_me
from .db import get_db
from .models import Admin, Audit, ErrorEvent, Order, PartnerApplication, PartnerUser, Payment, SecurityEvent, Store, now

r = APIRouter(prefix="/api/admin/console")

ACTIVE_LAB = ("placed", "confirmed", "assigned", "en_route", "arrived", "collected", "processing")
ACTIVE_MED = ("placed", "checking", "packing", "out")
LANE = {"placed": "new", "confirmed": "new", "checking": "new", "assigned": "way", "en_route": "way", "arrived": "way", "out": "way",
        "packing": "proc", "collected": "proc", "processing": "proc"}
DONE = ("ready", "delivered", "completed")
STUCK_MIN = {"placed": 20, "confirmed": 60, "checking": 30, "packing": 45, "assigned": 90, "en_route": 15, "arrived": 30, "out": 60,
             "collected": 240, "processing": 24 * 60}


def _ist(t: int):
    return time.gmtime(t + 19800)   # India has one time zone and no daylight saving


def mask(name: str) -> str:
    n = (name or "").strip().split()
    if not n:
        return "Family"
    return n[0][:1].upper() + "••••" + (" " + n[-1][:1].upper() + "." if len(n) > 1 else "")


def _last_t(o: Order) -> int:
    tl = o.timeline or []
    return max([int(x.get("t") or 0) for x in tl] + [o.created or 0])


def late_by(o: Order, t: int | None = None) -> int:
    """Minutes an active order is behind: no movement for longer than its step normally takes, or past the end of its slot."""
    t = t or now()
    lim = STUCK_MIN.get(o.status)
    if not lim:
        return 0
    behind = (t - _last_t(o)) // 60 - lim
    m = re.search(r"(\d{1,2})(?::(\d\d))?\s*(am|pm)?\s*[–-]\s*(\d{1,2})(?::(\d\d))?\s*(am|pm)", (o.slot or "").lower())
    if m and o.kind == "lab" and o.status in ("placed", "confirmed", "assigned", "en_route"):
        h = int(m.group(4)) % 12 + (12 if m.group(6) == "pm" else 0)
        lt = time.localtime(o.created or t)
        end = int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, int(m.group(5) or 0), 0, 0, 0, -1)))
        if end < (o.created or 0):
            end += 86400
        behind = max(behind, (t - end) // 60)
    return max(0, int(behind))


def card(o: Order, t: int) -> dict:
    items = o.items or []
    what = ", ".join(str(i.get("name") or "") for i in items[:2]) + (f" +{len(items) - 2}" if len(items) > 2 else "")
    area = ((o.addr or {}).get("area") or (o.address or "").split(",")[-1]).strip()[:40]
    return {"id": o.id, "kind": o.kind, "status": o.status, "lane": LANE.get(o.status, "done" if o.status in DONE else "other"),
            "what": what or ("Lab test" if o.kind == "lab" else "Medicines"), "who": mask(o.member or (o.household.name if o.household else "")),
            "area": area, "store": o.store.name if o.store else "", "storeId": o.store_id, "slot": o.slot, "total": o.total,
            "payment": o.payment, "late": 0 if t - _last_t(o) > 86400 else late_by(o, t), "stuck": (t - _last_t(o)) // 86400 if t - _last_t(o) > 86400 and o.status not in ("delivered", "ready", "cancelled", "refunded", "returned") else 0, "since": (t - _last_t(o)) // 60, "created": o.created,
            "rx": any(i.get("rx") for i in items), "verified": bool(o.verified_by), "agent": o.agent_id or "",
            "timeline": o.timeline or []}


@r.get("/board")
def board(kind: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    act = db.scalars(select(Order).where(Order.status.in_(ACTIVE_LAB + ACTIVE_MED)).order_by(Order.created.desc()).limit(500)).all()
    done = db.scalars(select(Order).where(Order.status.in_(DONE), Order.created > t - 86400).order_by(Order.created.desc()).limit(60)).all()
    rows = [card(o, t) for o in list(act) + list(done) if not kind or o.kind == kind]
    lanes = {k: [] for k in ("new", "way", "proc", "done")}
    for c in rows:
        lanes.get(c["lane"], lanes["done"]).append(c)
    for k in lanes:
        lanes[k].sort(key=lambda c: (-c["late"], -(c["created"] or 0)))
    agents = {u.id: {"name": u.name, "rating": u.rating} for u in db.scalars(select(PartnerUser).where(PartnerUser.id.in_({c["agent"] for c in rows if c["agent"]}))).all()} if rows else {}
    for c in rows:
        if c["agent"] in agents:
            c["agentName"] = agents[c["agent"]]["name"]
    return {"lanes": lanes, "counts": {k: len(v) for k, v in lanes.items()}, "late": sum(1 for c in rows if c["late"])}


def _week_bars(db: Session, t: int) -> list[dict]:
    out = []
    for d in range(6, -1, -1):
        lo = t - (d + 1) * 86400
        n = db.scalar(select(func.count(Order.id)).where(Order.created > lo, Order.created <= lo + 86400)) or 0
        out.append({"day": time.strftime("%a", _ist(lo + 86400)) if d else "Today", "n": n})
    return out


@r.get("/today")
def today(days: int = 7, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .onboard import checks, _plus_days
    t = now()
    days = 1 if days <= 1 else 30 if days >= 30 else 7
    since = t - days * 86400
    needs: list[dict] = []

    act = db.scalars(select(Order).where(Order.status.in_(ACTIVE_LAB + ACTIVE_MED))).all()
    # Over a day with no movement is not "late", it is stuck: someone has to close it or chase it.
    stuck = [o for o in act if t - _last_t(o) > 86400]
    late = [o for o in act if late_by(o, t) and o not in stuck]
    unacc = [o for o in act if o.status == "placed" and t - (o.created or t) > 600 and o not in stuck]
    if stuck:
        needs.append({"sev": "urgent", "tag": "Orders", "icon": "⏸", "title": f"{len(stuck)} order{'s are' if len(stuck) > 1 else ' is'} stuck for over a day",
                      "sub": f"#{stuck[0].id} · no update in {(t - _last_t(stuck[0])) // 86400} days · close it or call the partner", "act": "Open board", "go": "board"})
    if unacc:
        needs.append({"sev": "urgent", "tag": "Orders", "icon": "☎", "title": f"{len(unacc)} new order{'s' if len(unacc) > 1 else ''} not accepted in 10 min",
                      "sub": f"#{unacc[0].id} · {unacc[0].store.name if unacc[0].store else ''} · call the partner", "act": "Open board", "go": "board"})
    if late:
        worst = max(late, key=lambda o: late_by(o, t))
        needs.append({"sev": "urgent", "tag": "Orders", "icon": "!", "title": f"{len(late)} order{'s are' if len(late) > 1 else ' is'} running late",
                      "sub": f"#{worst.id} · {worst.store.name if worst.store else ''} · {late_by(worst, t)} min behind", "act": "Open board", "go": "board"})
    rx = [o for o in act if o.kind == "medicine" and any(i.get("rx") for i in (o.items or [])) and not o.verified_by]
    if rx:
        needs.append({"sev": "warn", "tag": "Orders", "icon": "℞", "title": f"{len(rx)} prescription order{'s' if len(rx) > 1 else ''} to check",
                      "sub": "Oldest waiting " + str(max((t - (o.created or t)) // 60 for o in rx)) + " min", "act": "Check", "go": "rx"})
    locked = db.scalars(select(Admin).where(Admin.locked_until > t)).all()
    if locked:
        needs.append({"sev": "urgent", "tag": "Security", "icon": "!", "title": f"{len(locked)} admin account{'s' if len(locked) > 1 else ''} locked",
                      "sub": ", ".join(x.email for x in locked[:2]) + " · too many wrong passwords", "act": "Review", "go": "trust"})
    stores = db.scalars(select(Store)).all()
    ready = [s for s in stores if s.active and not s.verified and all(c["done"] for c in checks(db, s))]
    if ready:
        needs.append({"sev": "warn", "tag": "Network", "icon": str(len(ready)), "title": f"{len(ready)} partner{'s' if len(ready) > 1 else ''} ready to go live",
                      "sub": ", ".join(s.name for s in ready[:3]), "act": "Open", "go": "labs"})
    apps = db.scalar(select(func.count(PartnerApplication.id)).where(PartnerApplication.status == "new")) or 0
    if apps:
        needs.append({"sev": "warn", "tag": "Network", "icon": str(apps), "title": f"{apps} new partner application{'s' if apps > 1 else ''}",
                      "sub": "Check the licence on the regulator's register", "act": "Review", "go": "applications"})
    claimed = db.scalars(select(Payment).where(Payment.status == "claimed")).all()
    if claimed:
        needs.append({"sev": "warn", "tag": "Money", "icon": "₹", "title": f"{len(claimed)} UPI payment{'s' if len(claimed) > 1 else ''} to match",
                      "sub": f"₹{sum(p.amount for p in claimed):,} · paid by families, not yet confirmed against the bank", "act": "Match", "go": "payments"})
    errs = db.scalars(select(ErrorEvent).where(ErrorEvent.last > t - 3600).order_by(ErrorEvent.count.desc())).all()
    if errs and sum(e.count for e in errs) >= 10:
        e = errs[0]
        needs.append({"sev": "info", "tag": "Tech", "icon": "⚠", "title": f"App error · {e.count} times recently",
                      "sub": f"\"{e.message[:70]}\" · {e.where[:40]}", "act": "See error", "go": "system"})
    soon = [s for s in stores if s.verified and (s.profile or {}).get("nablExpiry") and (s.profile or {})["nablExpiry"] < _plus_days(30)]
    if soon:
        needs.append({"sev": "info", "tag": "Network", "icon": "✉", "title": f"{len(soon)} licence{'s' if len(soon) > 1 else ''} expire within 30 days",
                      "sub": ", ".join(s.name for s in soon[:3]), "act": "Open", "go": "labs"})
    try:
        from .ops2 import open_counts
        for n in open_counts(db, t):
            needs.append(n)
    except ImportError:
        pass
    order = {"urgent": 0, "warn": 1, "info": 2}
    needs.sort(key=lambda n: order.get(n["sev"], 3))

    def period(lo, hi):
        o = db.scalars(select(Order).where(Order.created > lo, Order.created <= hi)).all()
        done = [x for x in o if x.status in DONE]
        lab_done = [x for x in done if x.kind == "lab"]
        return {"orders": len(done), "gross": sum(x.total or 0 for x in done),
                "ontime": round(100 * sum(1 for x in lab_done if not late_by(x, x.done_at or t)) / len(lab_done)) if lab_done else None}
    from .models import Household, HealthRecord
    cur, prev = period(since, t), period(since - days * 86400, since)
    fam = db.scalar(select(func.count(func.distinct(SecurityEvent.user_id))).where(SecurityEvent.t > since, SecurityEvent.kind.like("signin:%"))) or 0
    reps = db.scalar(select(func.count(HealthRecord.id)).where(HealthRecord.kind == "report", HealthRecord.created > since)) or 0
    reps_p = db.scalar(select(func.count(HealthRecord.id)).where(HealthRecord.kind == "report", HealthRecord.created > since - days * 86400, HealthRecord.created <= since)) or 0
    pct = lambda a_, b_: None if not b_ else round(100 * (a_ - b_) / b_)  # noqa: E731
    lanes = board(a=a, db=db)["counts"]
    live = {k: sum(1 for s in stores if s.kind == k and s.verified and s.active) for k in ("lab", "pharmacy", "hospital")}
    audit = db.scalars(select(Audit).order_by(Audit.t.desc()).limit(5)).all()
    return {
        "greeting": ("Good morning" if _ist(t).tm_hour < 12 else "Good afternoon" if _ist(t).tm_hour < 17 else "Good evening"),
        "needs": needs,
        "kpi": [{"label": "Families active", "value": fam, "delta": None},
                {"label": "Reports read", "value": reps, "delta": pct(reps, reps_p)},
                {"label": "Orders completed", "value": cur["orders"], "delta": pct(cur["orders"], prev["orders"])},
                {"label": "Gross value", "value": cur["gross"], "money": True, "delta": pct(cur["gross"], prev["gross"])},
                {"label": "On-time home visits", "value": cur["ontime"], "pct": True,
                 "delta": None if cur["ontime"] is None or prev["ontime"] is None else cur["ontime"] - prev["ontime"], "pts": True}],
        "now": {"new": lanes.get("new", 0), "way": lanes.get("way", 0), "proc": lanes.get("proc", 0), "late": len(late)},
        "week": _week_bars(db, t),
        "network": {"live": live, "waiting": sum(1 for s in stores if s.active and not s.verified), "pins": None,
                    "rating": round(sum(s.rating for s in stores if s.verified and s.rating_n) / max(1, sum(1 for s in stores if s.verified and s.rating_n)), 1) if any(s.rating_n for s in stores) else None},
        "system": {"version": (os.getenv("GIT_SHA") or os.getenv("APP_VERSION") or "dev")[:7],
                   "errors1h": sum(e.count for e in errs), "sms": bool(os.getenv("MSG91_AUTH_KEY") or os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("FIREBASE_WEB_API_KEY")),
                   "email": bool(os.getenv("SMTP_HOST") or os.getenv("RESEND_API_KEY") or os.getenv("SENDGRID_API_KEY")),
                   "ai": bool(os.getenv("ANTHROPIC_API_KEY")), "s3": bool(os.getenv("S3_BUCKET"))},
        "activity": [{"t": x.t, "who": x.who, "what": x.what} for x in audit],
    }


@r.get("/search")
def search(q: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    q = (q or "").strip()
    if len(q) < 2:
        return {"groups": []}
    ql = f"%{q.lower()}%"
    groups = []
    st = db.scalars(select(Store).where(func.lower(Store.name).like(ql) | func.lower(Store.area).like(ql) | func.lower(Store.licence).like(ql)).limit(6)).all()
    if st:
        groups.append({"name": "Partners", "items": [{"type": "partner", "id": s.id, "kind": s.kind, "title": s.name,
                                                     "sub": f"{s.kind.title()} · {s.area or s.city} · {'Live' if s.verified and s.active else 'Paused' if not s.active else 'Onboarding'}"} for s in st]})
    oid = q.upper().lstrip("#").replace("UH-", "")
    od = db.scalars(select(Order).where(Order.id.like(f"%{oid}%")).limit(5)).all() if len(oid) >= 3 else []
    if od:
        groups.append({"name": "Orders", "items": [{"type": "order", "id": o.id, "title": f"#{o.id} · " + (", ".join(i.get('name', '') for i in (o.items or [])[:2]) or o.kind),
                                                   "sub": f"{o.store.name if o.store else ''} · {o.status}"} for o in od]})
    pays = db.scalars(select(Payment).where(func.lower(Payment.utr).like(ql) | func.lower(Payment.note).like(ql)).limit(4)).all()
    if pays:
        groups.append({"name": "Payments", "items": [{"type": "payment", "id": p.id, "title": f"₹{p.amount:,} · {p.utr or p.note}", "sub": p.status} for p in pays]})
    acts = []
    for s in st[:2]:
        if s.verified and s.active:
            acts.append({"type": "action", "do": "pause", "id": s.id, "title": f"Pause {s.name}"})
        elif not s.verified:
            acts.append({"type": "action", "do": "open", "id": s.id, "kind": s.kind, "title": f"Continue onboarding {s.name}"})
    for word, go, title in (("late", "board", "Show late orders"), ("payout", "settlements", "Prepare payouts"), ("lock", "trust", "See locked accounts"),
                            ("lab", "labs", "Go to Labs"), ("pharm", "pharmacies", "Go to Pharmacies"), ("hosp", "hospitals", "Go to Hospitals"),
                            ("error", "system", "See app errors"), ("refund", "board", "Refund an order"), ("audit", "team", "Open audit log")):
        if word in q.lower():
            acts.append({"type": "go", "go": go, "title": title})
    if acts:
        groups.append({"name": "Actions", "items": acts})
    return {"groups": groups}


# ---- first-run checklist: what still stops the service from working end to end ---------------------------------------
def _env(*k: str) -> bool:
    return all(os.getenv(x) for x in k)


@r.get("/setup")
def setup(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from . import messaging
    from .models import Setting
    live_labs = db.scalar(select(func.count(Store.id)).where(Store.kind == "lab", Store.active == True, Store.verified == True)) or 0  # noqa: E712
    live_ph = db.scalar(select(func.count(Store.id)).where(Store.kind == "pharmacy", Store.active == True, Store.verified == True)) or 0  # noqa: E712
    rv = db.get(Setting, "reviewer")
    owners = db.scalars(select(Admin).where(Admin.role == "owner")).all()
    old_mail = [x.email for x in owners if x.email.split("@")[-1] != "urbanhealth.in"]
    items = [
        {"key": "partner", "group": "Go live", "name": "First live lab", "ok": live_labs > 0, "now": f"{live_labs} live",
         "why": "Families can book home tests only with a live lab.", "how": "Network → Labs → finish a lab's checklist → Go live.", "go": "labs"},
        {"key": "pharmacy", "group": "Go live", "name": "First live pharmacy", "ok": live_ph > 0, "now": f"{live_ph} live",
         "why": "Medicine orders need a pharmacy with a registered pharmacist.", "how": "Network → Pharmacies → finish the checklist → Go live.", "go": "pharmacies"},
        {"key": "reviewer", "group": "Go live", "name": "Clinical reviewer named", "ok": bool(rv and (rv.value or {}).get("name")), "now": "",
         "why": "Health guidance pages show who reviewed them.", "how": "Fill in the reviewer form below.", "go": "system"},
        {"key": "ai", "group": "Services", "name": "Smart reading of reports", "ok": _env("ANTHROPIC_API_KEY"), "now": "",
         "why": "Without it, uploaded reports are stored but values aren't read out.", "how": "Add ANTHROPIC_API_KEY to /etc/urbanhealth/env.yaml on the server, then restart.", "go": ""},
        {"key": "push", "group": "Services", "name": "Phone notifications", "ok": _env("VAPID_PRIVATE_KEY", "VAPID_SUBJECT"), "now": "",
         "why": "Medicine and visit reminders reach phones only with push keys.", "how": "Generate a VAPID key pair once and add VAPID_PRIVATE_KEY and VAPID_SUBJECT=mailto:support@urbanhealth.in.", "go": ""},
        {"key": "email", "group": "Services", "name": "Email", "ok": messaging.email_ready(), "now": "",
         "why": "Partner invites, receipts and sign-in codes by email.", "how": "Add RESEND_API_KEY (or SMTP_HOST, SMTP_USER, SMTP_PASS) and verify the urbanhealth.in domain.", "go": ""},
        {"key": "sms", "group": "Services", "name": "SMS alerts to partners", "ok": messaging.alert_sms_ready(), "now": "",
         "why": "A new order texts the lab owner; without it they see it only in the portal.", "how": "Register the alert template on DLT, then add MSG91_AUTH_KEY and MSG91_SOS_FLOW_ID.", "go": ""},
        {"key": "maps", "group": "Services", "name": "Google Maps", "ok": _env("GOOGLE_MAPS_KEY"), "now": "OpenStreetMap in use" if not _env("GOOGLE_MAPS_KEY") else "",
         "why": "Optional. OpenStreetMap works; Google gives sharper street detail.", "how": "Add GOOGLE_MAPS_KEY restricted to urbanhealth.in.", "go": "", "optional": True},
        {"key": "pay", "group": "Services", "name": "Online payments", "ok": _env("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"), "now": "UPI and cash only" if not _env("RAZORPAY_KEY_ID") else "",
         "why": "Optional. Cash and UPI at the door already work.", "how": "Create a Razorpay account, then add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.", "go": "", "optional": True},
        {"key": "files", "group": "Services", "name": "Document storage bucket", "ok": _env("S3_BUCKET"), "now": "in the database" if not _env("S3_BUCKET") else "",
         "why": "Optional for the pilot; a bucket is needed past a few thousand documents.", "how": "Create a private bucket and add S3_BUCKET with its keys.", "go": "", "optional": True},
        {"key": "grievance", "group": "Law", "name": "Grievance officer named", "ok": _env("GRIEVANCE_NAME", "GRIEVANCE_EMAIL"), "now": "",
         "why": "DPDP Act and the IT Rules require a named grievance officer.", "how": "Add GRIEVANCE_NAME and GRIEVANCE_EMAIL; they appear on the privacy page.", "go": ""},
        {"key": "adminmail", "group": "Security", "name": "Owner email on urbanhealth.in", "ok": not old_mail, "now": ", ".join(old_mail),
         "why": "Owner accounts use another domain; resets go to a mailbox you may not control.", "how": "On the server run: python -m api.admin_cli rename OLD NEW", "go": "team"},
    ]
    need = [i for i in items if not i["ok"] and not i.get("optional")]
    return {"items": items, "done": sum(1 for i in items if i["ok"] or i.get("optional")), "total": len(items), "need": len(need)}


@r.get("/funnel")
def funnel(days: int = 30, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Where families drop out of a booking. Screen opens come from the anonymous usage counter (no person attached)."""
    import datetime as _dt
    from .models import UsageDay
    days = max(1, min(90, days))
    since = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    cnt = dict(db.execute(select(UsageDay.screen, func.sum(UsageDay.n)).where(UsageDay.day >= since).group_by(UsageDay.screen)).all())
    placed = db.scalar(select(func.count(Order.id)).where(Order.kind == "lab", Order.created >= now() - days * 86400)) or 0
    done = db.scalar(select(func.count(Order.id)).where(Order.kind == "lab", Order.created >= now() - days * 86400, Order.status.in_(("ready", "collected", "processing")))) or 0
    steps = [("Opened lab tests", int(cnt.get("book-a-home-test", 0))), ("Compared labs", int(cnt.get("choose-a-lab", 0))),
             ("Reached checkout", int(cnt.get("confirm-booking", 0))), ("Booked", placed), ("Sample collected", done)]
    return {"days": days, "steps": [{"name": n, "n": v} for n, v in steps]}

"""Server-side medicine reminders and missed-dose alerts by Web Push.

Every minute: for each household that has push subscriptions, decrypt its state, work out which doses are due at each
member's reminder times (and which are still unticked an hour later), and push once per member, day and slot.
The state is read, never written: ticking a dose still happens in the app.
"""
from __future__ import annotations

import re
import threading
import time
from datetime import date as _dt_date, datetime, timedelta, timezone

from sqlalchemy import select

from . import push as PUSH
from .db import session
from .family import decrypt
from .models import HouseholdState, PushSub, ReminderSent, User

IST = timezone(timedelta(hours=5, minutes=30))
SLOTS = ["Morning", "Afternoon", "Evening", "Night"]
DEFAULT_TIMES = {"Morning": "08:00", "Afternoon": "14:00", "Evening": "18:00", "Night": "21:00"}
WD = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MISSED_AFTER_MIN = 60


def due_doses(state: dict, member: dict, slot: str, day: str) -> list[str]:
    taken = ((state.get("taken") or {}).get(member["id"]) or {})
    done = taken.get("s", {}) if taken.get("d") == day else {}
    off = (state.get("rem") or {}).get("off") or {}
    out = []
    for x in (state.get("meds") or {}).get(member["id"], []) or []:
        if off.get(x.get("id")):
            continue
        for j, w in enumerate(x.get("when") or []):
            if w == slot and not done.get(f"{x.get('id')}:{j}"):
                out.append(x.get("n", "medicine"))
    return out


REFILL_AT = 9 * 60          # 09:00 IST, once a day
REFILL_DAYS = 3


def doses_per_day(x: dict) -> float:
    """Daily slots count 1 each; a weekday entry ("Monday") counts 1/7."""
    n = 0.0
    for w in x.get("when") or []:
        n += 1 if w in SLOTS else (1 / 7 if w in WD else 0)
    return n


def days_left(x: dict) -> float | None:
    left = x.get("left")
    if left is None:
        return None
    per = doses_per_day(x)
    return (float(left) / per) if per else None


def low_meds(state: dict, member: dict) -> list[dict]:
    """Medicines with a stock count that runs out within REFILL_DAYS (or already has)."""
    out = []
    for x in (state.get("meds") or {}).get(member["id"], []) or []:
        d = days_left(x)
        if d is not None and d <= REFILL_DAYS:
            out.append({"id": x.get("id"), "n": x.get("n", "medicine"), "days": int(d), "left": x.get("left")})
    return out


def refill_text(items: list[dict]) -> str:
    parts = []
    for i in items:
        parts.append(f"{i['n']} — {'none left' if not i['left'] else ('today' if i['days'] < 1 else f'about {i['days']} day{'s' if i['days'] != 1 else ''} left')}")
    return "; ".join(parts)


def tick(now_dt: datetime | None = None) -> int:
    now_dt = now_dt or datetime.now(IST)
    try:
        with session() as db:
            daily_people(db, now_dt)
            from .surprise import deliver_due
            deliver_due(db)
            if now_dt.hour == 8:
                morning_people(db, now_dt)
                from .phase5 import send_morning_summary
                send_morning_summary(db)
            if now_dt.hour == 20 and now_dt.minute < 5:
                from .booking import evening_before
                evening_before(db)
            db.commit()
    except Exception as e:  # a daily check must never stop the dose reminders
        print("[reminders] daily:", type(e).__name__, str(e)[:120], flush=True)
    if not PUSH.ready():
        return 0
    day = now_dt.strftime("%Y-%m-%d")
    minute = now_dt.hour * 60 + now_dt.minute
    sent = 0
    with session() as db:
        hids = {s.household_id for s in db.scalars(select(PushSub)).all()}
        for hid in hids:
            st = db.get(HouseholdState, hid)
            if not st:
                continue
            try:
                state = decrypt(st.blob)
            except Exception:
                continue
            times = ((state.get("rem") or {}).get("times") or {})
            rem_on = (state.get("rem") or {}).get("on", True)
            subs = db.scalars(select(PushSub).where(PushSub.household_id == hid)).all()
            users = {u.id: u for u in db.scalars(select(User).where(User.household_id == hid)).all()}
            for m in state.get("members") or []:
                # refill: once a day, when a counted stock runs out within a few days
                if REFILL_AT <= minute <= REFILL_AT + 45:
                    key = f"{hid}:{m['id']}:{day}:refill"
                    low = low_meds(state, m)
                    if low and not db.get(ReminderSent, key):
                        db.add(ReminderSent(key=key))
                        first = (m.get("name") or "").split(" ")[0]
                        owner_ids = {uid for uid, u in users.items() if u.member_id == m["id"]}
                        for s in subs:
                            mine = s.user_id in owner_ids
                            if owner_ids and not mine:
                                continue
                            msg = {"title": "Refill soon" if mine else f"{first}: refill soon", "body": refill_text(low), "url": f"/app#refill={low[0]['id']}", "tag": f"refill-{m['id']}"}
                            ok, status, _ = PUSH.send(s.sub, msg)
                            if ok:
                                sent += 1
                            elif status in (404, 410):
                                db.delete(s)
                            else:
                                s.failures += 1
                for slot in SLOTS:
                    hh, mm = (times.get(slot) or DEFAULT_TIMES[slot]).split(":")
                    at = int(hh) * 60 + int(mm)
                    for kind, start, end in (("due", at, at + 45), ("missed", at + MISSED_AFTER_MIN, at + MISSED_AFTER_MIN + 45)):
                        if not (start <= minute <= end):
                            continue
                        key = f"{hid}:{m['id']}:{day}:{slot}:{kind}"
                        if db.get(ReminderSent, key):
                            continue
                        due = due_doses(state, m, slot, day)
                        if not due or (kind == "due" and not rem_on):
                            continue
                        db.add(ReminderSent(key=key))
                        first = (m.get("name") or "").split(" ")[0]
                        owner_ids = {uid for uid, u in users.items() if u.member_id == m["id"]}
                        for s in subs:
                            mine = s.user_id in owner_ids
                            if kind == "due":
                                # a person's own reminder goes to their own phone; profiles without an account are reminded through everyone
                                if owner_ids and not mine:
                                    continue
                                msg = {"title": f"{slot} medicines" if mine else f"{first}: {slot.lower()} medicines", "body": ", ".join(due), "url": "/app", "tag": f"dose-{m['id']}-{slot}"}
                            elif mine:
                                msg = {"title": f"Still to take: {slot.lower()} medicines", "body": ", ".join(due), "url": "/app", "tag": f"missed-{m['id']}-{slot}"}
                            else:
                                msg = {"title": f"{first} has not ticked {slot.lower()} medicines", "body": ", ".join(due) + " · an hour past the reminder", "url": "/app", "tag": f"missed-{m['id']}-{slot}"}
                            ok, status, _ = PUSH.send(s.sub, msg)
                            if ok:
                                sent += 1
                            elif status in (404, 410):
                                db.delete(s)
                            else:
                                s.failures += 1
        tick_people(db, now_dt)    # counted on its own: tick() keeps reporting the household reminders it always did
        # keep the dedupe table small
        db.query(ReminderSent).filter(ReminderSent.t < int(time.time()) - 3 * 86400).delete()
    return sent


# Reminder text in the language each recipient chose (Settings > Language). Medicine names stay as typed.
SAY = {
    "en": {"due_own": "Time for your {t} medicines", "due_other": "{first}: {t} medicines", "missed_own": "Still to take",
           "missed_other": "{first} has not taken the {t} medicines", "late": " · an hour past the reminder"},
    "ta": {"due_own": "உங்கள் {t} மருந்துகளுக்கான நேரம்", "due_other": "{first}: {t} மருந்துகள்", "missed_own": "இன்னும் எடுக்கவில்லை",
           "missed_other": "{first} {t} மருந்துகளை இன்னும் எடுக்கவில்லை", "late": " · நினைவூட்டலுக்குப் பின் ஒரு மணி நேரம்"},
    "te": {"due_own": "మీ {t} మందుల సమయం", "due_other": "{first}: {t} మందులు", "missed_own": "ఇంకా వేసుకోలేదు",
           "missed_other": "{first} {t} మందులు ఇంకా వేసుకోలేదు", "late": " · రిమైండర్ తర్వాత ఒక గంట"},
}


# Insulin: the reminder also says where the next injection should go, the same rotation the app shows
# (belly right/left, thighs, upper arms; the longest-rested area first).
INSULIN = re.compile(r"insulin|glargine|aspart|lispro|glulisine|degludec|detemir|mixtard|humulin|humalog|lantus|toujeo|novorapid|novomix|basalog|tresiba|ryzodeg|apidra|levemir|insugen|wosulin", re.I)
ZONES = ["belly-r", "belly-l", "thigh-r", "thigh-l", "arm-r", "arm-l"]
ZONE_SAY = {
    "en": {"belly-r": "belly, right side", "belly-l": "belly, left side", "thigh-r": "right thigh", "thigh-l": "left thigh", "arm-r": "right upper arm", "arm-l": "left upper arm", "next": "Next spot: {z}"},
    "ta": {"belly-r": "வயிறு, வலது பக்கம்", "belly-l": "வயிறு, இடது பக்கம்", "thigh-r": "வலது தொடை", "thigh-l": "இடது தொடை", "arm-r": "வலது மேல் கை", "arm-l": "இடது மேல் கை", "next": "அடுத்த இடம்: {z}"},
    "te": {"belly-r": "పొట్ట, కుడి వైపు", "belly-l": "పొట్ట, ఎడమ వైపు", "thigh-r": "కుడి తొడ", "thigh-l": "ఎడమ తొడ", "arm-r": "కుడి పై చేయి", "arm-l": "ఎడమ పై చేయి", "next": "తర్వాతి స్థలం: {z}"},
    "hi": {"belly-r": "पेट, दाईं ओर", "belly-l": "पेट, बाईं ओर", "thigh-r": "दाईं जाँघ", "thigh-l": "बाईं जाँघ", "arm-r": "दाईं ऊपरी बाँह", "arm-l": "बाईं ऊपरी बाँह", "next": "अगली जगह: {z}"},
}


def insulin_next(db, pid: str) -> str:
    """The area to use next: never used first, then the one used longest ago (ties in body order)."""
    from .models import HealthRecord
    last: dict[str, float] = {}
    for d in db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "dose")):
        dd = _safe(d) or {}
        site = str(dd.get("site") or "")
        z = re.sub(r"-\d$", "", site)
        if z in ZONES:
            try:
                at = float(dd.get("at") or 1)
            except (TypeError, ValueError):
                at = 1.0
            last[z] = max(last.get(z, 0.0), at)
    return sorted(ZONES, key=lambda z: (last.get(z, 0.0), ZONES.index(z)))[0]


def _zone_line(lang: str, zone: str) -> str:
    z = ZONE_SAY.get(lang) or ZONE_SAY["en"]
    return z["next"].format(z=z[zone])


def _say(lang: str, key: str, **kw) -> str:
    return (SAY.get(lang) or SAY["en"])[key].format(**kw)


def lang_of(db, uid: str) -> str:
    from .models import User
    u = db.get(User, uid)
    return (getattr(u, "lang", "") or "en") if u else "en"


def tick_people(db, now_dt: datetime) -> int:
    """Reminders for Phase 0 per-person medicines (/api/v2).

    At each dose time the person is reminded on their own phone; a dependent's guardians are reminded instead.
    An hour later, anything still unticked goes to the person and to the guardians. Nobody else is told: a medicine
    list is private unless shared, so reminders follow the same rule as reading it.
    """
    from .models import Guardian, HealthRecord, Person
    day0 = now_dt.strftime("%Y-%m-%d")
    minute0 = now_dt.hour * 60 + now_dt.minute
    subs_by_user: dict[str, list] = {}
    for s in db.scalars(select(PushSub)).all():
        subs_by_user.setdefault(s.user_id, []).append(s)
    if not subs_by_user:
        return 0
    sent = 0
    meds = db.scalars(select(HealthRecord).where(HealthRecord.kind == "med")).all()
    by_person: dict[str, list] = {}
    for x in meds:
        by_person.setdefault(x.person_id, []).append(x)
    for pid, rows in by_person.items():
        p = db.get(Person, pid)
        if not p or p.removed:
            continue
        # Each person's reminders run on their own clock: the time zone their phone saved with the medicine.
        day, minute = day0, minute0
        tz = ""
        for x in rows:
            try:
                tz = (decrypt(x.blob) or {}).get("tz") or ""
            except Exception:
                tz = ""
            if tz:
                break
        if tz and tz != "Asia/Kolkata":
            try:
                from zoneinfo import ZoneInfo
                ln = datetime.now(ZoneInfo(tz))
                day, minute = ln.strftime("%Y-%m-%d"), ln.hour * 60 + ln.minute
            except Exception:
                pass
        guardians = db.scalars(select(Guardian.user_id).where(Guardian.person_id == pid)).all() if p.owner_user is None else []
        owner = [p.owner_user] if p.owner_user else []
        if not any(u in subs_by_user for u in owner + list(guardians)):
            continue
        taken = set()
        for d in db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "dose", HealthRecord.day == day)):
            try:
                dd = decrypt(d.blob)
                taken.add((dd.get("med"), dd.get("time")))
            except Exception:
                continue
        at_time: dict[str, list[str]] = {}
        ins_at: set[str] = set()
        for x in rows:
            try:
                m = decrypt(x.blob)
            except Exception:
                continue
            if m.get("active") is False or (m.get("until") and str(m["until"]) < str(day)):
                continue   # a finished course stops reminding by itself
            if m.get("weekly") is not None and _dt_weekday(day) != int(m["weekly"]):
                continue   # once-a-week medicines remind on their own day only
            for t in m.get("times") or []:
                if (x.id, t) not in taken:
                    at_time.setdefault(t, []).append(_pill(m))
                    if INSULIN.search(str(m.get("name") or "")):
                        ins_at.add(t)
        first = (p.name or "").split(" ")[0]
        for t, names in at_time.items():
            try:
                hh, mm = t.split(":")
                at = int(hh) * 60 + int(mm)
            except ValueError:
                continue
            ids = [x.id for x in rows if (m := _safe(x)) and t in (m.get("times") or []) and (x.id, t) not in taken]
            zone = insulin_next(db, pid) if t in ins_at else ""
            snz = db.get(ReminderSent, f"snz:{pid}:{day}:{t}")
            for kind, start, end in (("due", at, at + 45), ("missed", at + MISSED_AFTER_MIN, at + MISSED_AFTER_MIN + 45), ("snooze", 0, 24 * 60)):
                if kind == "snooze":
                    if not snz or snz.t <= 1 or snz.t > int(time.time()):
                        continue
                    snz.t = 1   # fired once; the 3-day sweep removes it
                elif not (start <= minute <= end):
                    continue
                else:
                    key = f"v2:{pid}:{day}:{t}:{kind}"
                    if db.get(ReminderSent, key):
                        continue
                    db.add(ReminderSent(key=key))
                act = {"pid": pid, "day": day, "t": t, "meds": ids}
                if kind in ("due", "snooze"):
                    to = owner or list(guardians)
                    msg = lambda own, lang="en": {"title": _say(lang, "due_own" if own else "due_other", t=t, first=first), "body": ", ".join(names) + (" · " + _zone_line(lang, zone) if zone else ""), "url": "/app/meds", "tag": f"dose-{pid}-{t}", "act": act}
                else:
                    to = owner + list(guardians)
                    msg = lambda own, lang="en": {"title": _say(lang, "missed_own" if own else "missed_other", t=t, first=first), "body": ", ".join(names) + ("" if own else _say(lang, "late")), "url": "/app/meds", "tag": f"missed-{pid}-{t}", "act": act}
                from .inbox import wants_push
                for uid in to:
                    if not wants_push(db, uid, "reminder"):
                        continue
                    for s in subs_by_user.get(uid, []):
                        ok, status, _ = PUSH.send(s.sub, msg(uid == p.owner_user, lang_of(db, uid)))
                        if ok:
                            sent += 1
                        elif status in (404, 410):
                            db.delete(s)
                        else:
                            s.failures += 1
    return sent


def morning_people(db, now_dt: datetime) -> int:
    """8 a.m. good-morning push, for accounts that turned it on: today's doses for them and the people they look after,
    and any follow-up visit today. Only people whose medicines they manage; one push per account per day."""
    from .inbox import notify
    from .models import Guardian, HealthRecord, NoticePref, Person
    day = now_dt.strftime("%Y-%m-%d")
    sent = 0
    for pr in db.scalars(select(NoticePref)).all():
        if (pr.prefs or {}).get("morning") is not True:
            continue
        key = f"morning:{pr.user_id}:{day}"
        if db.get(ReminderSent, key):
            continue
        u = db.get(User, pr.user_id)
        if not u or not u.household_id:
            continue
        ppl = list(db.scalars(select(Person).where(Person.owner_user == u.id, Person.removed.is_(None))))
        ppl += [p for p in (db.get(Person, g) for g in db.scalars(select(Guardian.person_id).where(Guardian.user_id == u.id))) if p and not p.removed]
        parts = []
        for p in ppl:
            doses, fu = 0, None
            for x in db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind.in_(("med", "visitnote")))):
                d = _safe(x) or {}
                if x.kind == "med" and d.get("active") is not False and not (d.get("until") and str(d["until"]) < day):
                    if d.get("weekly") is None or _dt_weekday(day) == int(d["weekly"]):
                        doses += len(d.get("times") or [])
                elif x.kind == "visitnote" and d.get("follow") == day:
                    fu = d.get("doctor") or d.get("place") or "the doctor"
            who = "You" if p.owner_user == u.id else (p.name or "").split(" ")[0]
            bit = []
            if doses:
                bit.append(f"{doses} dose{'s' if doses != 1 else ''}")
            if fu:
                bit.append(f"follow-up with {fu}")
            if bit:
                parts.append(f"{who}: " + ", ".join(bit))
        db.add(ReminderSent(key=key))
        if not parts:
            continue
        notify(db, u.household_id, "reminder", "Good morning", " · ".join(parts)[:180], {}, url="/app", to_user=u.id)
        sent += 1
    return sent


def daily_people(db, now_dt: datetime) -> int:
    """Once a day (9 a.m. IST): medicines running out within 5 days, and a gentle note to family members who can
    see the medicines when someone has missed two or more doses since yesterday morning. In-app notice + push."""
    from .inbox import notify
    from .models import Grant, Guardian, HealthRecord, Person
    if not (9 * 60 <= now_dt.hour * 60 + now_dt.minute < 10 * 60):
        return 0
    day = now_dt.strftime("%Y-%m-%d")
    yday = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    done = 0
    meds: dict[str, list] = {}
    for x in db.scalars(select(HealthRecord).where(HealthRecord.kind == "med")).all():
        meds.setdefault(x.person_id, []).append(x)
    for pid, rows in meds.items():
        p = db.get(Person, pid)
        if not p or p.removed:
            continue
        first = (p.name or "").split(" ")[0]
        # refill
        for x in rows:
            try:
                m = decrypt(x.blob)
            except Exception:
                continue
            if m.get("active") is False or not m.get("stock") or not m.get("stockDay") or m.get("until"):   # a fixed course is not refilled
                continue
            per = max(1, len(m.get("times") or []) or 1)
            try:
                gone = (now_dt.date() - datetime.fromisoformat(m["stockDay"]).date()).days * per
                left_days = (float(m["stock"]) - gone) / per
            except Exception:
                continue
            key = f"refill:{x.id}:{m['stockDay']}"
            if left_days <= 5 and not db.get(ReminderSent, key):
                db.add(ReminderSent(key=key))
                left = max(0, int(left_days))
                notify(db, p.household_id, "meds", f"{m.get('name')} {'runs out today' if left == 0 else f'runs out in {left} day' + ('s' if left != 1 else '')}",
                       "Reorder now so there is no gap.", {"person": pid, "med": x.id}, member_id=pid, url="/app/meds")
                done += 1
        # two or more missed doses since yesterday → tell the people allowed to see the medicines
        missed = db.query(ReminderSent).filter(ReminderSent.key.like(f"v2:{pid}:{yday}:%:missed") | ReminderSent.key.like(f"v2:{pid}:{day}:%:missed")).count()
        key = f"family:{pid}:{day}"
        if missed >= 2 and not db.get(ReminderSent, key):
            db.add(ReminderSent(key=key))
            fam = [g.user_id for g in db.scalars(select(Grant).where(Grant.person_id == pid, Grant.level == "all"))]
            fam += list(db.scalars(select(Guardian.user_id).where(Guardian.person_id == pid)))
            for uid in set(fam) - {p.owner_user}:
                notify(db, p.household_id, "meds", f"{first} missed {missed} doses since yesterday", "A gentle call might help. Nothing else is shared.", {"person": pid}, member_id=pid, url="/app/meds", to_user=uid)
                done += 1
    # insurance renewal: 30, 7 and 1 day before the policy ends, to the household
    from .models import SchemeCard
    for days in (30, 7, 1):
        due = (now_dt + timedelta(days=days)).strftime("%Y-%m-%d")
        for c in db.scalars(select(SchemeCard).where(SchemeCard.valid_until == due)).all():
            key = f"renew:{c.id}:{due}:{days}"
            if db.get(ReminderSent, key):
                continue
            db.add(ReminderSent(key=key))
            name = c.insurer or "Your health insurance"
            notify(db, c.household_id, "insurance", f"{name} renews {'tomorrow' if days == 1 else f'in {days} days'}",
                   "Renew before it lapses so waiting periods are not reset.", {"card": c.id}, url="/app/insurance")
            done += 1
    # follow-up visits the doctor asked for: a note the day before, to the person (or a dependent's guardians)
    tmr = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    for x in db.scalars(select(HealthRecord).where(HealthRecord.kind == "visitnote", HealthRecord.day >= (now_dt - timedelta(days=200)).strftime("%Y-%m-%d"))).all():
        n = _safe(x) or {}
        if n.get("follow") != tmr:
            continue
        key = f"follow:{x.id}"
        p = db.get(Person, x.person_id)
        if not p or p.removed or db.get(ReminderSent, key):
            continue
        db.add(ReminderSent(key=key))
        first = (p.name or "").split(" ")[0]
        who = n.get("doctor") or n.get("place") or "the doctor"
        to = [p.owner_user] if p.owner_user else list(db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id)))
        for uid in to:
            notify(db, p.household_id, "visits", f"Follow-up tomorrow with {who}" if p.owner_user == uid else f"{first}'s follow-up tomorrow with {who}",
                   "Book a time or call the OP desk.", {"person": p.id}, member_id=p.id, url="/app/visits", to_user=uid)
            done += 1
    # confirmed hospital visits: the evening before (after 7 pm) and about an hour before
    from .models import Appointment, Store
    today_s = now_dt.strftime("%Y-%m-%d")
    for a in db.scalars(select(Appointment).where(Appointment.status == "confirmed", Appointment.kind == "visit",
                                                  ((Appointment.slot_date == tmr) | (Appointment.slot_date == today_s) |
                                                   ((Appointment.slot_date == "") & Appointment.date.in_((tmr, today_s)))))).all():
        d, t = (a.slot_date or a.date), (a.slot_time or a.time or "")[:5]
        st = db.get(Store, a.store_id)
        where = st.name if st else "the hospital"
        who = (a.member_name or "").split(" ")[0]
        if d == tmr and now_dt.hour >= 19 and not db.get(ReminderSent, f"visit:eve:{a.id}"):
            db.add(ReminderSent(key=f"visit:eve:{a.id}"))
            notify(db, a.household_id, "visits", f"Tomorrow{' ' + _t12(t) if t else ''} · {where}", f"{who + chr(39) + 's visit' if who else 'Your visit'}{' with ' + a.doctor if a.doctor else ''}. Take the insurance card and recent reports.",
                   {"appointment": a.id}, member_id=a.member_id, url="/app/visits")
            done += 1
        elif d == today_s and t and re.fullmatch(r"\d{2}:\d{2}", t):
            mins = int(t[:2]) * 60 + int(t[3:]) - (now_dt.hour * 60 + now_dt.minute)
            if 0 < mins <= 75 and not db.get(ReminderSent, f"visit:1h:{a.id}"):
                db.add(ReminderSent(key=f"visit:1h:{a.id}"))
                notify(db, a.household_id, "visits", f"Visit at {_t12(t)} · {where}", "Leave now to arrive 15 minutes early. Tap I'm here at the desk to get your token.",
                       {"appointment": a.id}, member_id=a.member_id, url="/app/visits")
                done += 1
    # a child turning 18: the guardians are told a month ahead and on the day; a teen with their own login stops
    # having guardians on their 18th birthday (the guardians keep the summary they could already see)
    from .models import Grant as _G
    for p in db.scalars(select(Person).where(Person.removed.is_(None))).all():
        gs = list(db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id)))
        if not gs:
            continue
        dob = (_safe_profile(p) or {}).get("dob", "")
        try:
            b = _dt_date.fromisoformat(dob)
        except (TypeError, ValueError):
            continue
        try:
            bday = b.replace(year=b.year + 18)
        except ValueError:
            bday = b.replace(year=b.year + 18, day=28)
        days = (bday - now_dt.date()).days
        first = (p.name or "").split(" ")[0]
        if days in (30, 0):
            key = f"eighteen:{p.id}:{days}"
            if not db.get(ReminderSent, key):
                db.add(ReminderSent(key=key))
                for uid in gs:
                    if p.owner_user:
                        notify(db, p.household_id, "family", f"{first} turns 18 {'today' if days == 0 else 'next month'}",
                               "From 18 they manage their own health. You keep seeing their summary until they change it.", {"person": p.id}, member_id=p.id, url="/app", to_user=uid)
                    else:
                        notify(db, p.household_id, "family", f"{first} turns 18 {'today' if days == 0 else 'next month'}",
                               "Give them their own login from Family. Their records move with them.", {"person": p.id}, member_id=p.id, url="/app", to_user=uid)
                done += 1
        if days <= 0 and p.owner_user:
            for uid in gs:
                db.merge(_G(person_id=p.id, user_id=uid, level="summary", womens=False))
                db.execute(Guardian.__table__.delete().where(Guardian.person_id == p.id, Guardian.user_id == uid))
    return done


def _safe_profile(p):
    try:
        from .people import profile
        return profile(p)
    except Exception:
        return {}


def _t12(t: str) -> str:
    h, m = int(t[:2]), t[3:5]
    return f"{(h % 12) or 12}:{m} {'AM' if h < 12 else 'PM'}"


def start() -> None:
    from api.tasks import in_process_loops

    if not PUSH.ready():
        print("[reminders] VAPID_PRIVATE_KEY not set; server-side reminders are off", flush=True)
        return
    if not in_process_loops():
        print("[reminders] in-process loop off; Cloud Scheduler drives /api/v1/tasks/reminders", flush=True)
        return

    def loop():
        while True:
            try:
                from api.tasks import _run
                _run("reminders", 55, tick)          # through the lease, so the standby sees it ran
            except Exception as e:
                print("[reminders] tick failed:", type(e).__name__, str(e)[:200], flush=True)
            time.sleep(60)

    threading.Thread(target=loop, name="reminders", daemon=True).start()
    print("[reminders] server-side reminders on", flush=True)


def _pill(m: dict) -> str:
    """A medicine as an elder recognises it: the name, then its colour and shape."""
    look = " ".join(x for x in (m.get("look") or "", (m.get("shape") or "").lower()) if x)
    return (m.get("name") or "medicine") + (f" ({look})" if look else "")


def _safe(x):
    try:
        return decrypt(x.blob)
    except Exception:
        return None


def _dt_weekday(day: str) -> int:
    """0 = Sunday … 6 = Saturday, the way the app stores a weekly medicine's day."""
    import datetime as _d
    return (_d.date.fromisoformat(str(day)[:10]).weekday() + 1) % 7

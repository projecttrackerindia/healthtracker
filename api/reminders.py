"""Server-side medicine reminders and missed-dose alerts by Web Push.

Every minute: for each household that has push subscriptions, decrypt its state, work out which doses are due at each
member's reminder times (and which are still unticked an hour later), and push once per member, day and slot.
The state is read, never written: ticking a dose still happens in the app.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

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
            if now_dt.hour == 8:
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
                    at_time.setdefault(t, []).append(m.get("name") or "medicine")
        first = (p.name or "").split(" ")[0]
        for t, names in at_time.items():
            try:
                hh, mm = t.split(":")
                at = int(hh) * 60 + int(mm)
            except ValueError:
                continue
            for kind, start, end in (("due", at, at + 45), ("missed", at + MISSED_AFTER_MIN, at + MISSED_AFTER_MIN + 45)):
                if not (start <= minute <= end):
                    continue
                key = f"v2:{pid}:{day}:{t}:{kind}"
                if db.get(ReminderSent, key):
                    continue
                db.add(ReminderSent(key=key))
                if kind == "due":
                    to = owner or list(guardians)
                    msg = lambda own: {"title": f"Time for your {t} medicines" if own else f"{first}: {t} medicines", "body": ", ".join(names), "url": "/app/meds", "tag": f"dose-{pid}-{t}"}
                else:
                    to = owner + list(guardians)
                    msg = lambda own: {"title": "Still to take" if own else f"{first} has not taken the {t} medicines", "body": ", ".join(names) + (" · an hour past the reminder" if not own else ""), "url": "/app/meds", "tag": f"missed-{pid}-{t}"}
                from .inbox import wants_push
                for uid in to:
                    if not wants_push(db, uid, "reminder"):
                        continue
                    for s in subs_by_user.get(uid, []):
                        ok, status, _ = PUSH.send(s.sub, msg(uid == p.owner_user))
                        if ok:
                            sent += 1
                        elif status in (404, 410):
                            db.delete(s)
                        else:
                            s.failures += 1
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
    return done


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
                tick()
            except Exception as e:
                print("[reminders] tick failed:", type(e).__name__, str(e)[:200], flush=True)
            time.sleep(60)

    threading.Thread(target=loop, name="reminders", daemon=True).start()
    print("[reminders] server-side reminders on", flush=True)


def _dt_weekday(day: str) -> int:
    """0 = Sunday … 6 = Saturday, the way the app stores a weekly medicine's day."""
    import datetime as _d
    return (_d.date.fromisoformat(str(day)[:10]).weekday() + 1) % 7

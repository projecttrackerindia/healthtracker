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
    if not PUSH.ready():
        return 0
    now_dt = now_dt or datetime.now(IST)
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
        # keep the dedupe table small
        db.query(ReminderSent).filter(ReminderSent.t < int(time.time()) - 3 * 86400).delete()
    return sent


def start() -> None:
    if not PUSH.ready():
        print("[reminders] VAPID_PRIVATE_KEY not set; server-side reminders are off", flush=True)
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

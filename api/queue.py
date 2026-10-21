"""The OP queue: one doctor, one day, a list of people in the order they arrived.

Walk-ins are most of Indian outpatient care and they are not appointments. There is no slot, only an order
of arrival and a number called out across a waiting room. So the model is the number, restarted at 1 for
each doctor each day, exactly as every OP counter in the country already works — and a family with a
confirmed appointment joins the same queue when they arrive, because one list the counter can see beats two
it has to reconcile in its head.

The wait estimate is the one place this could easily lie. It is computed from how long this doctor has
actually taken today, and when there is not enough of the day behind us to say, it says so rather than
inventing a number. A wrong "10 minutes" is worse than no estimate: it is the reason people stop watching
the screen and crowd the door.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .inbox import notify
from .models import Appointment, Household, PartnerUser, Store, Token, now

r = APIRouter(prefix="/api/v1")           # the family's side
pr = APIRouter(prefix="/api/partner")     # the counter's side
IST = timezone(timedelta(hours=5, minutes=30))

OPEN_STATES = ("waiting", "called", "in")
# Below this many finished consultations we have not seen enough of the doctor's day to estimate from it.
MIN_SAMPLE = 3
# A long first consultation of the morning should not set the expectation for the whole queue.
SAMPLE_KEEP = 8


def today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def doctor_of(db: Session, store_id: str, doctor_id: str) -> PartnerUser:
    d = db.get(PartnerUser, doctor_id)
    if not d or d.store_id != store_id or d.role != "doctor" or not d.active:
        raise HTTPException(404, "That doctor is not seeing patients here.")
    return d


def pace(db: Session, store_id: str, doctor_id: str, day: str) -> int | None:
    """Median minutes per consultation for this doctor today, or None when the day is too young to say."""
    rows = db.scalars(select(Token).where(Token.store_id == store_id, Token.doctor_id == doctor_id,
                                          Token.day == day, Token.state == "done")
                      .order_by(Token.done_at.desc()).limit(SAMPLE_KEEP)).all()
    spans = [t.done_at - t.started_at for t in rows if t.done_at and t.started_at and t.done_at > t.started_at]
    if len(spans) < MIN_SAMPLE:
        return None
    spans.sort()
    mid = spans[len(spans) // 2]
    return max(1, round(mid / 60))


def ahead_of(db: Session, t: Token) -> int:
    """How many people are still in front. Counts the one in the room, because they are."""
    return db.scalar(select(func.count(Token.id)).where(
        Token.store_id == t.store_id, Token.doctor_id == t.doctor_id, Token.day == t.day,
        Token.state.in_(OPEN_STATES), Token.number < t.number)) or 0


def token_json(db: Session, t: Token, *, counter: bool = False) -> dict:
    d = db.get(PartnerUser, t.doctor_id)
    out = {"id": t.id, "number": t.number, "state": t.state, "day": t.day, "kind": t.kind,
           "member": t.member, "why": t.why, "created": t.created,
           "doctor": (d.name or "") if d else "", "doctorId": t.doctor_id,
           "calledAt": t.called_at, "startedAt": t.started_at, "doneAt": t.done_at}
    if counter:
        out["phone"] = t.phone
        out["householdId"] = t.household_id
        out["waitedMin"] = max(0, round((now() - t.created) / 60))
        return out
    ahead = ahead_of(db, t) if t.state == "waiting" else 0
    p = pace(db, t.store_id, t.doctor_id, t.day)
    out["ahead"] = ahead
    # Stated only when the day itself supports it. "We will know once a few people have been through" is a
    # better thing to show a waiting room than a confident number nobody can keep to.
    out["waitMin"] = ahead * p if (p and t.state == "waiting") else None
    out["pacing"] = bool(p)
    return out


# ---- the family joins ------------------------------------------------------------------------------------------------
class JoinIn(BaseModel):
    store: str
    doctor: str
    member: str = ""
    memberId: str = ""
    phone: str = ""
    why: str = ""
    appointment: str = ""


def household(db: Session, key: str | None) -> Household:
    h = db.scalar(select(Household).where(Household.key == (key or "")))
    if not h:
        raise HTTPException(400, "missing household key")
    return h


@r.post("/queue")
def join(body: JoinIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Take a number. One live token per person per doctor per day, so a family tapping twice in a waiting
    room does not end up behind themselves."""
    from .auth import limit

    limit(request, "queue", 20, 600)
    h = household(db, x_dokko_key)
    s = db.get(Store, body.store)
    if not s or not s.active or s.kind != "hospital":
        raise HTTPException(404, "That clinic is not taking patients here.")
    d = doctor_of(db, s.id, body.doctor)
    if not d.verified:
        raise HTTPException(400, "This doctor's registration is still being checked.")
    day = today()
    mine = db.scalar(select(Token).where(Token.household_id == h.id, Token.doctor_id == d.id,
                                         Token.day == day, Token.state.in_(OPEN_STATES),
                                         Token.member_id == (body.memberId or "")))
    if mine:
        return token_json(db, mine)

    appt = None
    if body.appointment:
        appt = db.get(Appointment, body.appointment)
        if not appt or appt.household_id != h.id or appt.store_id != s.id:
            raise HTTPException(404, "appointment not found")

    last = db.scalar(select(func.max(Token.number)).where(Token.store_id == s.id, Token.doctor_id == d.id,
                                                          Token.day == day)) or 0
    t = Token(store_id=s.id, doctor_id=d.id, household_id=h.id, member_id=body.memberId or "",
              member=(body.member or "")[:80], phone=(body.phone or "")[:20], why=(body.why or "")[:160],
              day=day, number=last + 1, kind="appointment" if appt else "walkin",
              appt_id=appt.id if appt else "", state="waiting", created=now())
    db.add(t)
    db.flush()
    return token_json(db, t)


@r.get("/queue/{tid}")
def my_token(tid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    t = db.get(Token, tid)
    if not t or t.household_id != h.id:
        raise HTTPException(404)
    return token_json(db, t)


@r.get("/queue")
def my_tokens(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    rows = db.scalars(select(Token).where(Token.household_id == h.id, Token.day == today(),
                                          Token.state.in_(OPEN_STATES)).order_by(Token.created)).all()
    return {"tokens": [token_json(db, t) for t in rows]}


@r.post("/queue/{tid}/leave")
def leave(tid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """They gave up, or came another day. Freeing the place keeps everybody else's estimate honest."""
    h = household(db, x_dokko_key)
    t = db.get(Token, tid)
    if not t or t.household_id != h.id:
        raise HTTPException(404)
    if t.state in ("done", "skipped"):
        return token_json(db, t)
    t.state, t.done_at = "skipped", now()
    return token_json(db, t)


# ---- the counter -----------------------------------------------------------------------------------------------------
from .partner import me as partner_me  # noqa: E402  (imported here to keep partner.py's own imports acyclic)


def _counter(u: PartnerUser = Depends(partner_me)) -> PartnerUser:
    """Anybody working the counter can run the queue — the receptionist calls the numbers, not the doctor."""
    if u.role not in ("owner", "staff", "doctor"):
        raise HTTPException(403, "This is the OP counter.")
    return u


@pr.get("/doctors")
def doctors(db: Session = Depends(get_db), u: PartnerUser = Depends(_counter)):
    """Who is seeing patients here, with how many are waiting for each."""
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == u.store_id,
                                                PartnerUser.role == "doctor").order_by(PartnerUser.name)).all()
    day = today()
    out = []
    for d in rows:
        waiting = db.scalar(select(func.count(Token.id)).where(
            Token.doctor_id == d.id, Token.day == day, Token.state == "waiting")) or 0
        inroom = db.scalar(select(Token).where(Token.doctor_id == d.id, Token.day == day,
                                               Token.state.in_(("called", "in"))))
        out.append({"id": d.id, "name": d.name or d.email, "specialty": d.specialty or "",
                    "regNo": d.reg_no or "", "verified": bool(d.verified), "active": d.active,
                    "waiting": waiting, "paceMin": pace(db, u.store_id, d.id, day),
                    "withNow": inroom.number if inroom else None})
    return {"doctors": out, "day": day}


@pr.get("/queue")
def counter_queue(doctor: str = "", db: Session = Depends(get_db), u: PartnerUser = Depends(_counter)):
    """Today's list for one doctor. A doctor signing in sees their own without having to pick."""
    did = doctor or (u.id if u.role == "doctor" else "")
    if not did:
        raise HTTPException(400, "Choose a doctor.")
    d = doctor_of(db, u.store_id, did)
    day = today()
    rows = db.scalars(select(Token).where(Token.store_id == u.store_id, Token.doctor_id == d.id,
                                          Token.day == day).order_by(Token.number)).all()
    live = [t for t in rows if t.state in OPEN_STATES]
    return {"doctor": {"id": d.id, "name": d.name or d.email, "specialty": d.specialty or ""},
            "day": day, "paceMin": pace(db, u.store_id, d.id, day),
            "waiting": sum(1 for t in live if t.state == "waiting"),
            "seen": sum(1 for t in rows if t.state == "done"),
            "tokens": [token_json(db, t, counter=True) for t in rows]}


NEXT_STATE = {"waiting": "called", "called": "in", "in": "done"}
MOVE_LABEL = {"called": "Called", "in": "With the doctor", "done": "Seen", "skipped": "Skipped"}


def _move(db: Session, t: Token, to: str, u: PartnerUser) -> dict:
    s = db.get(Store, t.store_id)
    if t.state == to:
        return token_json(db, t, counter=True)
    t.state = to
    stamp = now()
    if to == "called":
        t.called_at = stamp
        notify(db, t.household_id, "appointment", f"{s.name if s else 'Clinic'}: token {t.number} called",
               "Please come to the consulting room.", {"token": t.id, "number": t.number, "state": to},
               t.member_id or "", "/app")
    elif to == "in":
        t.started_at = stamp
    elif to == "done":
        t.done_at = stamp
        if not t.started_at:
            t.started_at = t.called_at or stamp
    elif to == "skipped":
        t.done_at = stamp
        notify(db, t.household_id, "appointment", f"{s.name if s else 'Clinic'}: token {t.number} was passed over",
               "You were not at the room when your number came up. Ask at the counter to be put back in.",
               {"token": t.id, "number": t.number, "state": to}, t.member_id or "", "/app")
    return token_json(db, t, counter=True)


def _token(db: Session, u: PartnerUser, tid: str) -> Token:
    t = db.get(Token, tid)
    if not t or t.store_id != u.store_id:
        raise HTTPException(404, "token not found")
    if u.role == "doctor" and t.doctor_id != u.id:
        raise HTTPException(403, "That token is in another doctor's queue.")
    return t


class MoveIn(BaseModel):
    to: str


@pr.post("/queue/{tid}/move")
def move(tid: str, body: MoveIn, db: Session = Depends(get_db), u: PartnerUser = Depends(_counter)):
    """Call, start, finish or pass over. Only forwards, except skip, which is available at any open state."""
    t = _token(db, u, tid)
    to = body.to
    if to == "skipped":
        if t.state in ("done", "skipped"):
            raise HTTPException(400, "That one is already finished.")
        return _move(db, t, "skipped", u)
    if to != NEXT_STATE.get(t.state):
        raise HTTPException(400, f"From '{t.state}' the next step is "
                                 f"'{NEXT_STATE.get(t.state, 'nothing')}', not '{to}'.")
    return _move(db, t, to, u)


@pr.post("/queue/next")
def call_next(doctor: str = "", db: Session = Depends(get_db), u: PartnerUser = Depends(_counter)):
    """Finish whoever is in the room and call the next number, in one tap — which is the whole job at an OP
    counter and should not be two."""
    did = doctor or (u.id if u.role == "doctor" else "")
    if not did:
        raise HTTPException(400, "Choose a doctor.")
    d = doctor_of(db, u.store_id, did)
    day = today()
    cur = db.scalar(select(Token).where(Token.doctor_id == d.id, Token.day == day,
                                        Token.state.in_(("called", "in"))).order_by(Token.number))
    if cur:
        _move(db, cur, "done", u)
    nxt = db.scalar(select(Token).where(Token.doctor_id == d.id, Token.day == day,
                                        Token.state == "waiting").order_by(Token.number))
    if not nxt:
        return {"called": None, "finished": cur.id if cur else None, "waiting": 0}
    out = _move(db, nxt, "called", u)
    db.flush()      # the count below must see the two states just changed, not the ones before
    left = db.scalar(select(func.count(Token.id)).where(Token.doctor_id == d.id, Token.day == day,
                                                        Token.state == "waiting")) or 0
    return {"called": out, "finished": cur.id if cur else None, "waiting": left}


@pr.post("/queue/add")
def counter_add(body: JoinIn, db: Session = Depends(get_db), u: PartnerUser = Depends(_counter)):
    """Somebody who walked in and is not on the app. Most of a morning's queue, in most clinics.

    No household is attached, so nothing is sent to a phone — the number is written on a slip and called in
    the room, which is how it already works."""
    d = doctor_of(db, u.store_id, body.doctor or "")
    if not (body.member or "").strip():
        raise HTTPException(400, "A name, so the room can call them by it.")
    day = today()
    last = db.scalar(select(func.max(Token.number)).where(Token.store_id == u.store_id,
                                                          Token.doctor_id == d.id, Token.day == day)) or 0
    t = Token(store_id=u.store_id, doctor_id=d.id, household_id="", member=body.member.strip()[:80],
              phone=(body.phone or "")[:20], why=(body.why or "")[:160], day=day, number=last + 1,
              kind="walkin", state="waiting", created=now())
    db.add(t)
    db.flush()
    return token_json(db, t, counter=True)

"""Telling the family: a pregnancy shared as a surprise, and a birth shared as news.

Nothing goes out until she sends it. The notification never carries the news ("Jyothsna sent you something"); it is
opened inside the app, and only then does the person follow the pregnancy: week, due date and stage, never her cycle or
notes. If she says the pregnancy ended, anything unopened is cancelled and following stops, quietly."""
from __future__ import annotations

import datetime as _dt

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import csrf, limit, need_user
from .db import get_db
from .inbox import notify
from .models import Person, Surprise, User, now
from .people import active_pregnancy, my_person, profile

r = APIRouter(prefix="/api/v2", dependencies=[Depends(csrf)])
WAYS = ("gift", "countdown", "inperson", "card")


def _first(p: Person | None, db: Session | None = None) -> str:
    """What the family calls them: their call name, else the given name they typed at sign-up, else the first word."""
    if not p:
        return "Your family"
    c = (profile(p).get("callName") or "").strip()
    if c:
        return c
    if db is not None and p.owner_user:
        ou = db.get(User, p.owner_user)
        g = ((ou.name if ou else "") or "").strip().split(" ")[0]
        if g and g.lower() in (p.name or "").lower():
            return g
    return (p.name or "").split(" ")[0] or "Your family"


def _t12(ts: int) -> str:
    d = _dt.datetime.fromtimestamp(ts, _dt.timezone(_dt.timedelta(hours=5, minutes=30)))
    return d.strftime("%-I:%M %p")


def deliver(db: Session, s: Surprise) -> None:
    """Send the notice for one surprise. Gift and card at their time; a countdown announces itself at once."""
    if s.delivered or s.status != "active":
        return
    me = db.get(Person, s.from_person)
    who = _first(me, db)
    if s.kind == "born":
        title, body = f"{who} has news for you 💛", "Open it to see."
    elif s.way == "countdown":
        title, body = f"{who} sent you something 🎁", f"It opens at {_t12(s.deliver_at)}. Be together when it does."
    else:
        title, body = f"{who} sent you something 🎁", "Open it when you're together."
    s.delivered = now()
    if s.way != "inperson":
        notify(db, s.household_id, "family", title, body, {"surprise": s.id}, url=f"/app#surprise={s.id}", to_user=s.to_user)


def deliver_due(db: Session) -> int:
    """Called from the minute loop: gifts whose time has come."""
    n = 0
    for s in db.scalars(select(Surprise).where(Surprise.delivered.is_(None), Surprise.status == "active", Surprise.deliver_at <= now())).all():
        deliver(db, s)
        n += 1
    return n


class To(BaseModel):
    person: str
    way: str = "card"


class ShareIn(BaseModel):
    to: list[To] = []
    note: str = ""
    at: int = 0          # unix time to deliver; 0 = now
    kind: str = "pregnancy"
    baby: str = ""       # kind=born: the new baby's person id


@r.post("/news/share")
def share(body: ShareIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, f"news:{u.id}", 30, 3600)
    me = my_person(db, u)
    if not me:
        raise HTTPException(400, "Finish your profile first")
    kind = "born" if body.kind == "born" else "pregnancy"
    pg = active_pregnancy(db, me.id) or {}
    extra = None
    if kind == "pregnancy":
        if pg.get("stage") != "pregnant":
            raise HTTPException(400, "Turn on pregnancy mode first")
    else:
        b = db.get(Person, body.baby)
        if not b or b.household_id != me.household_id or b.owner_user is not None:
            raise HTTPException(404, "Baby not found")
        bp = profile(b)
        extra = {"baby": b.id, "name": b.name, "dob": bp.get("dob", ""), "time": bp.get("birthTime", ""), "weight": bp.get("weight", ""),
                 "hospital": bp.get("birthHospital", "") or pg.get("hospital", ""), "sex": bp.get("sex", "")}
    when = body.at if body.at and body.at > now() else now()
    out = []
    for t in body.to[:20]:
        p = db.get(Person, t.person)
        if not p or p.household_id != me.household_id or not p.owner_user or p.owner_user == u.id:
            continue    # only adults with their own login, in this family
        way = t.way if t.way in WAYS else "card"
        if kind == "born":
            way = "card"
        old = db.scalar(select(Surprise).where(Surprise.from_person == me.id, Surprise.to_user == p.owner_user, Surprise.kind == kind, Surprise.status == "active"))
        if old and kind == "pregnancy":
            continue    # one surprise per person per pregnancy
        s = Surprise(household_id=me.household_id, from_person=me.id, from_user=u.id, to_user=p.owner_user, kind=kind, way=way,
                     note=body.note.strip()[:300], extra=extra, deliver_at=now() if way in ("countdown", "inperson") else when)
        if way == "countdown":
            s.deliver_at = when
        db.add(s)
        db.flush()
        if way == "inperson":
            s.delivered = now()
        elif way == "countdown" or s.deliver_at <= now():
            deliver(db, s)
        out.append(s.id)
    db.commit()
    return {"ok": True, "sent": len(out), "ids": out}


def _view(db: Session, s: Surprise, me: User) -> dict:
    p = db.get(Person, s.from_person)
    to = db.scalar(select(Person).where(Person.owner_user == s.to_user))
    d = {"id": s.id, "kind": s.kind, "way": s.way, "from": _first(p, db), "fromPerson": s.from_person, "to": _first(to, db), "toPerson": to.id if to else "",
         "deliverAt": s.deliver_at, "delivered": s.delivered, "opened": s.opened, "reply": s.reply, "status": s.status, "mine": s.from_user == me.id}
    # the news itself only once it may be opened
    if s.opened or s.from_user == me.id or (s.delivered and s.deliver_at <= now()):
        d["note"] = s.note
        if s.kind == "born":
            d["baby"] = s.extra or {}
        else:
            pg = active_pregnancy(db, s.from_person) or {}
            d["pregnancy"] = {"week": pg.get("week"), "due": pg.get("due"), "stage": pg.get("stage")}
    return d


@r.get("/surprises")
def surprises(u: User = Depends(need_user), db: Session = Depends(get_db)):
    got = db.scalars(select(Surprise).where(Surprise.to_user == u.id, Surprise.status == "active", Surprise.delivered.is_not(None))
                     .order_by(Surprise.created.desc()).limit(20)).all()
    sent = db.scalars(select(Surprise).where(Surprise.from_user == u.id).order_by(Surprise.created.desc()).limit(40)).all()
    return {"received": [_view(db, s, u) for s in got if s.way != "inperson"], "sent": [_view(db, s, u) for s in sent]}


def _mine(db: Session, u: User, sid: str) -> Surprise:
    s = db.get(Surprise, sid)
    if not s or u.id not in (s.to_user, s.from_user) or s.status != "active":
        raise HTTPException(404, "Not found")
    return s


@r.post("/surprises/{sid}/open")
def open_it(sid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    s = _mine(db, u, sid)
    if s.from_user == u.id and s.way != "inperson":
        raise HTTPException(403, "This one is for them to open")
    if s.deliver_at > now():
        raise HTTPException(409, f"It opens at {_t12(s.deliver_at)}")
    first = not s.opened
    s.opened = s.opened or now()
    if first and s.way != "inperson":
        to = db.scalar(select(Person).where(Person.owner_user == s.to_user))
        notify(db, s.household_id, "family", f"{_first(to, db)} opened your {'news' if s.kind == 'born' else 'surprise'} ❤️",
               f"At {_t12(s.opened)}", {"surprise": s.id}, url="/app", to_user=s.from_user)
    db.commit()
    return _view(db, s, u)


class ReplyIn(BaseModel):
    text: str = ""


@r.post("/surprises/{sid}/reply")
def reply(sid: str, body: ReplyIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    s = _mine(db, u, sid)
    if s.to_user != u.id:
        raise HTTPException(403, "Only they can reply")
    s.reply = body.text.strip()[:300] or "❤️"
    to = db.scalar(select(Person).where(Person.owner_user == u.id))
    notify(db, s.household_id, "family", f"{_first(to, db)} replied", s.reply, {"surprise": s.id}, url="/app", to_user=s.from_user)
    db.commit()
    return {"ok": True}


@r.get("/pregnancy/following")
def following(u: User = Depends(need_user), db: Session = Depends(get_db)):
    """The pregnancies this person was told about and opened: week, due date, stage. Nothing else of hers."""
    out, seen = [], set()
    for s in db.scalars(select(Surprise).where(Surprise.to_user == u.id, Surprise.kind == "pregnancy", Surprise.status == "active", Surprise.opened.is_not(None))).all():
        if s.from_person in seen:
            continue
        seen.add(s.from_person)
        p = db.get(Person, s.from_person)
        pg = active_pregnancy(db, s.from_person) or {}
        if not p or p.household_id != u.household_id or pg.get("stage") not in ("pregnant", "after"):
            continue
        out.append({"person": p.id, "name": _first(p, db), "stage": pg.get("stage"), "week": pg.get("week"), "due": pg.get("due"),
                    "born": pg.get("born", ""), "hospital": pg.get("hospital", ""), "doctor": pg.get("doctor", "")})
    return {"rows": out}


class EndIn(BaseModel):
    reason: str   # born | loss | mistake


@r.post("/pregnancy/end")
def end(body: EndIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """She turned pregnancy mode off. Unopened surprises never arrive; after a loss or a mistake, nobody keeps following."""
    me = my_person(db, u)
    if not me:
        raise HTTPException(400, "No profile")
    n = 0
    for s in db.scalars(select(Surprise).where(Surprise.from_person == me.id, Surprise.kind == "pregnancy", Surprise.status == "active")).all():
        if not s.opened:
            s.status = "cancelled"
            n += 1
        elif body.reason in ("loss", "mistake"):
            s.status = "stopped"
            n += 1
    db.commit()
    return {"ok": True, "changed": n}

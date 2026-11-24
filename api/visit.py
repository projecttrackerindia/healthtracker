"""Board 10 · the doctor's consult screen for an outpatient token.

Three things meet on one screen: what the family chose to show (summary, latest values against the last visit,
allergies, medicines), the same 3D body they see, and a prescription the doctor speaks.

What the family shares is theirs: their app sends it for this visit only, it is sealed with the server key, and it
is deleted when the visit ends or after 8 hours, whichever comes first. The doctor's speech becomes a draft and
nothing else: medicines the doctor did not say are not added, and fields they did not say stay empty. Nothing
reaches the family until the doctor signs.
"""
from __future__ import annotations

import json
import re
import time
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import storage
from .db import get_db
from .inbox import notify
from .models import Order, PartnerUser, Store, Token, VisitRx, VisitShare, now
from .partner import me as partner_me

r = APIRouter(prefix="/api/v1")
pr = APIRouter(prefix="/api/partner")

KEEP = 8 * 3600
MAX_CTX = 60_000


# ---- the family shares, for this visit only --------------------------------------------------------------------------
class ShareIn(BaseModel):
    ctx: dict


def _family_token(db: Session, tid: str, key: str | None) -> Token:
    from .queue import household
    h = household(db, key)
    t = db.get(Token, tid)
    if not t or t.household_id != h.id:
        raise HTTPException(404)
    return t


@r.post("/queue/{tid}/share")
def share(tid: str, body: ShareIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    t = _family_token(db, tid, x_dokko_key)
    if t.state in ("done", "skipped", "left"):
        raise HTTPException(409, "This visit is over.")
    raw = json.dumps(body.ctx, ensure_ascii=False)
    if len(raw) > MAX_CTX:
        raise HTTPException(413, "That summary is too large to share.")
    row = db.get(VisitShare, tid) or VisitShare(token_id=tid, store_id=t.store_id, household_id=t.household_id, blob=b"")
    row.blob, row.expires, row.t = storage.seal(raw.encode()), now() + KEEP, now()
    db.add(row)
    return {"shared": True, "until": row.expires}


@r.delete("/queue/{tid}/share")
def unshare(tid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _family_token(db, tid, x_dokko_key)
    row = db.get(VisitShare, tid)
    if row:
        db.delete(row)
    return {"shared": False}


def drop_share(db: Session, tid: str) -> None:
    """Called when the visit ends: what was shared for it goes with it."""
    row = db.get(VisitShare, tid)
    if row:
        db.delete(row)


def _ctx(db: Session, t: Token) -> dict | None:
    row = db.get(VisitShare, t.id)
    if not row:
        return None
    if row.expires < now():
        db.delete(row)
        return None
    try:
        return json.loads(storage.unseal(row.blob).decode())
    except Exception:
        return None


# ---- the doctor's side --------------------------------------------------------------------------------------------
def _doc_token(db: Session, u: PartnerUser, tid: str) -> Token:
    if u.role not in ("doctor", "owner"):
        raise HTTPException(403, "The consult screen is for doctors.")
    t = db.get(Token, tid)
    if not t or t.store_id != u.store_id:
        raise HTTPException(404, "token not found")
    if u.role == "doctor" and t.doctor_id != u.id:
        raise HTTPException(403, "That token is in another doctor's queue.")
    return t


def _usual_pharmacy(db: Session, household_id: str) -> str:
    o = db.scalar(select(Order).where(Order.household_id == household_id, Order.kind == "medicine")
                  .order_by(Order.created.desc()).limit(1))
    s = db.get(Store, o.store_id) if o else None
    return s.name if s else ""


@pr.get("/queue/{tid}/visit")
def visit(tid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    t = _doc_token(db, u, tid)
    past = db.scalars(select(Token).where(Token.store_id == t.store_id, Token.household_id == t.household_id,
                                          Token.member == t.member, Token.state == "done", Token.id != t.id)
                      .order_by(Token.done_at.desc())).all()
    last_rx = None
    if past:
        lr = db.scalar(select(VisitRx).where(VisitRx.token_id.in_([p.id for p in past])).order_by(VisitRx.t.desc()).limit(1))
        if lr:
            d = db.get(PartnerUser, lr.doctor_id)
            last_rx = {"t": lr.t, "doctor": d.name if d else "", "diagnosis": (lr.rx or {}).get("diagnosis", ""), "advice": (lr.rx or {}).get("advice", "")}
    mine = db.get(VisitRx, t.id)
    return {"token": {"id": t.id, "number": t.number, "member": t.member, "why": t.why, "state": t.state, "kind": t.kind,
                      "calledAt": t.called_at, "startedAt": t.started_at},
            "ctx": _ctx(db, t), "pastVisits": len(past), "lastVisit": last_rx or ({"t": past[0].done_at} if past else None),
            "usualPharmacy": _usual_pharmacy(db, t.household_id), "rx": mine.rx if mine else None,
            "doctor": {"name": u.name, "regNo": u.reg_no or "", "verified": bool(u.verified)}}


# ---- after the visit: what the doctor wants watched, on the family's body map ---------------------------------------
class WatchItem(BaseModel):
    label: str
    org: str = ""
    code: str = ""
    pos: list[float] | None = None


class WatchIn(BaseModel):
    items: list[WatchItem]


@pr.post("/queue/{tid}/watch")
def watch(tid: str, body: WatchIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """The doctor marks a few things to keep an eye on. They land in the person's record as the doctor's note, and show
    on the same body the family opens at home. Doctors only; the family cannot write or change them."""
    from .family import decrypt, encrypt
    from .models import HealthRecord, Person
    t = _doc_token(db, u, tid)
    if u.role != "doctor":
        raise HTTPException(403, "Only the doctor sends these.")
    if t.state not in ("called", "in", "done"):
        raise HTTPException(409, "Call the patient in first.")
    items = []
    for it in body.items[:6]:
        lb = it.label.strip()[:60]
        if not lb:
            continue
        pos = it.pos if it.pos and len(it.pos) == 3 and all(abs(v) < 100 for v in it.pos) else None
        items.append({"label": lb, "org": re.sub(r"[^a-z]", "", it.org.lower())[:16], "code": re.sub(r"[^a-z0-9_]", "", it.code.lower())[:16], "pos": pos})
    if not items:
        raise HTTPException(400, "Choose at least one thing to watch.")
    p = db.get(Person, t.member_id) if t.member_id else None
    if not p or p.household_id != t.household_id or p.removed:
        raise HTTPException(409, "This token is not linked to a family member, so there is no body map to send to.")
    s = db.get(Store, t.store_id)
    data = {"items": items, "doctor": u.name, "specialty": u.specialty or "", "store": s.name if s else "", "token": t.id, "t": now()}
    old = [x for x in db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind == "watch"))]
    for x in old:   # one note per visit: sending again replaces it
        if (decrypt(x.blob) or {}).get("token") == t.id:
            db.delete(x)
    db.add(HealthRecord(person_id=p.id, kind="watch", blob=encrypt(data), day=time.strftime("%Y-%m-%d"), by_user="partner:" + u.id))
    notify(db, t.household_id, "watch", f"Dr {u.name} marked what to watch",
           "; ".join(i["label"] for i in items[:3]) + (" …" if len(items) > 3 else "") + ". It is on your body map.",
           {"token": t.id, "doctor": u.name}, t.member_id or "", "/app")
    return {"ok": True, "items": items}


# ---- speech to a draft --------------------------------------------------------------------------------------------
NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90,
        "hundred": 100, "two hundred fifty": 250, "five hundred": 500, "thousand": 1000, "one thousand": 1000}
FREQ_WORDS = [("bd", r"twice|two times|\bbd\b|\bbid\b|1-0-1|morning and night"), ("tds", r"three times|thrice|\btds\b|\btid\b|1-1-1"),
              ("qid", r"four times|\bqid\b"), ("hs", r"at night|bedtime|before bed|\bhs\b|0-0-1"),
              ("sos", r"when needed|if needed|as needed|\bsos\b|\bprn\b"), ("weekly", r"once a week|weekly"),
              ("od", r"once a day|once daily|\bod\b|every morning|1-0-0")]
DOSE = {"od": "1-0-0", "bd": "1-0-1", "tds": "1-1-1", "qid": "1-1-1-1", "hs": "0-0-1", "sos": "when needed", "weekly": "weekly"}


def _words_to_num(s: str) -> str:
    for w, n in sorted(NUMW.items(), key=lambda x: -len(x[0])):
        s = re.sub(rf"\b{w}\b", str(n), s, flags=re.I)
    return s


def _vocab(current: list[dict]) -> list[tuple[str, str]]:
    """(spoken prefix, canonical name): what the doctor is taking about. Their current medicines first."""
    from .ai import BRANDS
    from .medlist import NAMES
    out = []
    for m in current:
        n = str(m.get("name") or "").strip()
        if n:
            out.append((n.split()[0].lower(), n))
    for n in NAMES:
        g = n.split()[0]
        if len(g) >= 4:
            out.append((g.lower(), g))
    for b in BRANDS:
        out.append((b.split()[0].lower(), b.split()[0].title()))
    return out


def local_draft(text: str, current: list[dict]) -> dict:
    """A rules reading of what the doctor said. Used when smart drafting is off, and as its safety net."""
    from .ai import CANON, LAB
    t = _words_to_num(text)
    vocab = _vocab(current)
    items, tests, advice, seen = [], [], [], set()
    for clause in re.split(r"[.;\n]|,\s*(?=[a-z]+\b)", t):
        c = clause.strip()
        if not c:
            continue
        lc = c.lower()
        hit, spoken = None, ""
        is_test = bool(re.search(r"\b(repeat|test|check|recheck)\b", lc))
        for word in ([] if is_test else re.findall(r"[a-z]{4,}", lc)):
            if word in ("same", "make", "continue", "increase", "decrease", "reduce", "stop", "start", "twice", "daily", "with", "after", "before", "food", "night", "morning"):
                continue
            for pre, canon in vocab:
                cp = len(__import__("os").path.commonprefix([pre, word]))
                if (pre.startswith(word) or word.startswith(pre) or (cp >= 4 and cp >= 0.75 * len(word))) and canon.lower() not in seen:
                    hit, spoken = canon, word
                    break
            if hit:
                break
        if is_test:
            for code, (rx, *_rest) in LAB.items():
                if re.search(rf"(?i){rx}", c):
                    when = re.search(r"in (\d+)\s*(day|week|month)s?", lc)
                    tests.append({"code": code, "name": CANON.get(code, code), "when": f"{when.group(1)} {when.group(2)}s" if when else ""})
                    break
            continue
        if re.search(r"\b(walk|exercise|diet|salt|sugar|sleep|water|smok|alcohol)\b", lc) and not hit:
            a = re.sub(r"\s+", " ", c).strip().rstrip(".")
            a = re.sub(r"(\d+)\s*minutes?", r"\1 min", a)
            advice.append(a[:1].upper() + a[1:] + ("" if re.search(r"daily|a day|every", a) else " daily"))
            continue
        if not hit:
            continue
        seen.add(hit.lower())
        cur = next((m for m in current if str(m.get("name") or "").lower().startswith(hit.lower().split()[0])), None)
        num = re.findall(r"(\d+(?:\.\d+)?)\s*(mg|mcg|iu|g\b|ml)?", lc[max(0, lc.find(spoken)):])
        strength = ""
        for n, unit in num:
            if float(n) >= 1 and not re.search(rf"{n}\s*(day|week|month|min)", lc):
                strength = f"{n} {unit or 'mg'}"
                break
        freq = next((k for k, rx in FREQ_WORDS if re.search(rx, lc)), "")
        dur = re.search(r"for (\d+)\s*(day|week|month)s?", lc)
        same = bool(re.search(r"\b(same|continue|as before|no change)\b", lc)) and not strength
        cur_strength = (re.search(r"\d+(?:\.\d+)?\s*(?:mg|mcg|iu|g|ml)", str(cur.get("name", "")) + " " + str(cur.get("strength", "")), re.I) if cur else None)
        if same and cur:
            strength = cur_strength.group(0) if cur_strength else ""
        if not freq and cur and re.search(r"\b(same|continue|as before|make it|increase|reduce|decrease)\b", lc):
            # "continue atorva but make it 20": the timing they did not change stays what it was
            freq = next((k for k, v in DOSE.items() if v == str(cur.get("dose") or "")), "")
        items.append({"name": re.sub(r"\s+\d.*$", "", str(cur.get("name"))) if cur else hit, "strength": strength, "form": "tablet",
                      "frequency": freq, "duration": f"{dur.group(1)} {dur.group(2)}s" if dur else "", "instructions": "", "heard": c[:160],
                      "was": {"strength": cur_strength.group(0) if cur_strength else "", "dose": str(cur.get("dose") or "")} if cur else None,
                      "same": same})
    return {"items": items, "tests": tests, "advice": advice}


def _status(it: dict) -> str:
    was = it.get("was")
    if not was:
        return "new"
    if it.get("same"):
        return "same"
    ws = re.sub(r"\s", "", (was.get("strength") or "").lower())
    ns = re.sub(r"\s", "", (it.get("strength") or "").lower())
    wd, nd = (was.get("dose") or "").lower(), DOSE.get(it.get("frequency") or "", "")
    if (ns and ws and ns != ws) or (nd and wd and nd not in wd and wd not in nd):
        return "changed"
    return "same"


class DraftIn(BaseModel):
    text: str


@pr.post("/queue/{tid}/rx-draft")
def rx_draft(tid: str, body: DraftIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """What the doctor said, as a draft prescription marked against what the patient takes now. Saves nothing."""
    t = _doc_token(db, u, tid)
    text = re.sub(r"\s+", " ", body.text or "").strip()[:4000]
    if len(text) < 3:
        raise HTTPException(400, "Say the prescription first.")
    ctx = _ctx(db, t) or {}
    current = [m for m in (ctx.get("medicines") or ctx.get("meds") or []) if isinstance(m, dict)][:30]
    from .rxlang import to_english
    english = to_english(text)
    d = local_draft(english, current)
    if english != text:
        d["english"] = english   # shown to the doctor so they can see what was understood
    for it in d["items"]:
        it["status"] = _status(it)
        if it.get("same") and not it["frequency"]:
            it["dose"] = (it["was"] or {}).get("dose", "")
            it["frequency"] = next((k for k, v in DOSE.items() if v == it["dose"]), "")
        else:
            it["dose"] = DOSE.get(it["frequency"], "")
    d["note"] = ("Drafted from what you said, read in English. " if d.get("english") else "Drafted from what you said. ") + "Check every line and fill anything blank before you sign."
    return d


# ---- sign and send ------------------------------------------------------------------------------------------------
class RxItem(BaseModel):
    name: str
    strength: str = ""
    form: str = ""
    frequency: str = ""
    duration: str = ""
    instructions: str = ""


class RxIn(BaseModel):
    items: list[RxItem]
    advice: str = ""
    followUp: str = ""
    diagnosis: str = ""
    tests: list[dict] = []


@pr.put("/queue/{tid}/rx")
def rx_sign(tid: str, body: RxIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    from .consult import FREQS, rx_pdf
    t = _doc_token(db, u, tid)
    if u.role != "doctor" or not u.reg_no:
        raise HTTPException(403, "Only a doctor with a registration number signs a prescription.")
    if t.state not in ("called", "in", "done"):
        raise HTTPException(409, "Call the patient in before you sign.")
    if not body.items or len(body.items) > 15:
        raise HTTPException(400, "1 to 15 medicines.")
    items = []
    for it in body.items:
        if not it.name.strip():
            raise HTTPException(400, "Every medicine needs a name.")
        if it.frequency.strip().lower() not in FREQS:
            raise HTTPException(400, f"How often should {it.name.strip()[:40]} be taken? Choose one.")
        items.append({"name": it.name.strip()[:80], "strength": it.strength.strip()[:30], "form": it.form.strip()[:20],
                      "frequency": it.frequency.strip().lower()[:12], "duration": it.duration.strip()[:30], "instructions": it.instructions.strip()[:80], "rx": True})
    tests = [{"code": str(x.get("code", ""))[:12], "name": str(x.get("name", ""))[:60], "when": str(x.get("when", ""))[:20]} for x in body.tests[:6] if x.get("name")]
    s = db.get(Store, t.store_id)
    rx = {"items": items, "advice": body.advice.strip()[:800], "followUp": (body.followUp.strip() or ", ".join(f"{x['name']} in {x['when']}" for x in tests if x["when"]))[:60],
          "diagnosis": body.diagnosis.strip()[:160], "tests": tests, "doctor": u.name, "regNo": u.reg_no, "specialty": u.specialty, "store": s.name if s else "", "t": now()}
    a = SimpleNamespace(id=t.id, member_name=t.member, why=t.why)
    try:
        pdf = rx_pdf(a, s, u, rx, visit="OP visit")
        storage.put(db, t.household_id, f"erx_{t.id}", pdf, "application/pdf", f"Prescription · Dr {u.name} · {time.strftime('%d-%m-%Y')}", "partner:" + u.id)
    except Exception as e:
        print("[visit] rx store failed:", type(e).__name__, str(e)[:200], flush=True)
        raise HTTPException(502, "The prescription could not be stored right now; try again in a minute.")
    row = db.get(VisitRx, t.id) or VisitRx(token_id=t.id, store_id=t.store_id, household_id=t.household_id, member_id=t.member_id or "", doctor_id=u.id)
    row.rx, row.t = rx, now()
    db.add(row)
    pharm = _usual_pharmacy(db, t.household_id)
    names = ", ".join(i["name"] for i in items[:3]) + (" …" if len(items) > 3 else "")
    notify(db, t.household_id, "prescription", f"Prescription from Dr {u.name}",
           f"{names}." + (f" Order from {pharm} in one tap." if pharm else " Open Medicines to order.") + (f" {tests[0]['name']} in {tests[0]['when']}." if tests and tests[0]["when"] else ""),
           {"token": t.id, "fileId": f"erx_{t.id}", "store": s.name if s else "", "doctor": u.name, "items": items, "tests": tests,
            "mime": "application/pdf", "name": f"Prescription · Dr {u.name}", "diagnosis": rx["diagnosis"], "pharmacy": pharm},
           t.member_id or "", "/app")
    return {"ok": True, "rx": rx, "usualPharmacy": pharm}



# ---- the family reads a prescription, in their own language ---------------------------------------------------------
def family_rx(db: Session, kind: str, rid: str, key: str | None):
    from .queue import household
    from .models import Appointment
    h = household(db, key)
    if not h:
        raise HTTPException(404)
    if kind == "visit":
        row = db.get(VisitRx, rid)
        if not row or row.household_id != h.id:
            raise HTTPException(404)
        return row
    a = db.get(Appointment, rid)
    if not a or a.household_id != h.id or not a.rx:
        raise HTTPException(404)
    return a


@r.get("/rx/{kind}/{rid}")
def rx_read(kind: str, rid: str, lang: str = "", db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """The signed prescription as the family sees it; with ?lang=ta (etc.) also a reading in that language.
    The English stays the record; the reading is kept on it so it says the same thing every time it is opened."""
    from sqlalchemy.orm.attributes import flag_modified

    from .rxlang import LANGS, cached
    row = family_rx(db, kind, rid, x_dokko_key)
    rx = dict(row.rx or {})
    out = {"rx": {k: v for k, v in rx.items() if k != "tr"}, "langs": LANGS, "fileId": f"erx_{rid}", "kind": kind, "id": rid, "member": getattr(row, "member_id", "") or ""}
    if lang and lang != "en":
        reading, changed = cached(rx, lang)
        if changed:
            rx.setdefault("tr", {})
            rx["tr"] = {**(rx.get("tr") or {}), lang: reading}
            row.rx = rx
            flag_modified(row, "rx")
        out["reading"] = reading
    return out

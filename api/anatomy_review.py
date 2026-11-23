"""Research-team review of the anatomy models we built or reshaped ourselves.

Most of the 3D body comes straight from published atlases (Z-Anatomy / BodyParts3D, the HuBMAP Human Reference
Atlas, the Visible Human Project). A few pieces are our own work on top of them: tissue blocks drawn after HuBMAP
illustrations, linings added around atlas organs, the female body's muscles and bones fitted from the male ones, and
the cleaned-up Visible Human sections. Each of those is listed in ITEMS. A reviewer opens it in the app, then marks it
Approved or Needs changes with a note. The family-facing close-up then says "Checked by our research team" instead of
"Being checked by our research team".

Reviews live in one Setting row (key "anatomy-review"):
  {item_id: {"state": "pending" | "approved" | "changes", "at": epoch, "by": email,
             "notes": [{"at", "by", "state", "text"}]}}
The public read returns only the state and the date, never who reviewed it or what they wrote.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .admin import Admin, log
from .admin import me as admin_me
from .db import get_db
from .models import Setting, now

r = APIRouter(prefix="/api/v1/anatomy")
xr = APIRouter(prefix="/api/admin/anatomy")

KEY = "anatomy-review"
STATES = ("pending", "approved", "changes")

# id, where it opens in the app, title, what we made ourselves, what it is built on
ITEMS = [
    ("x-alveoli", "lungs · Go deeper · Air sacs", "Air sacs (alveoli)",
     "Whole tissue block: air sacs, capillary net, type 1 and 2 cells, macrophage.",
     "Drawn after HuBMAP lung tissue-unit illustrations (CC BY 4.0)"),
    ("x-nephron", "kidneys · Go deeper · Kidney filter", "Kidney filter (nephron)",
     "Whole unit: glomerulus, Bowman capsule, tubules, loop of Henle, collecting duct, vessels.",
     "Drawn after HuBMAP kidney tissue-unit illustrations (CC BY 4.0)"),
    ("x-skin", "skin · Skin layers", "Skin layers",
     "Whole block: epidermis layers, dermis, fat, hair follicle, sweat and oil glands, vessels, nerve endings.",
     "Drawn after HuBMAP skin tissue-unit illustrations (CC BY 4.0)"),
    ("x-meninges", "brain · Linings", "Brain linings (meninges)",
     "Dura, arachnoid and pia around the atlas brain, with the main venous sinuses.",
     "Brain regions: Allen Human Brain Atlas via HuBMAP HRA (CC BY 4.0)"),
    ("x-pleura", "lungs · Linings", "Lung linings (pleura)",
     "Visceral and parietal pleura and the pleural space around the atlas lungs.",
     "Lungs and trachea: HuBMAP HRA (CC BY 4.0)"),
    ("x-throat", "ear, nose & throat · Throat", "Throat lining",
     "Mucosa of the pharynx and larynx, tonsils and the vocal folds' surface.",
     "Cartilages, muscles and bones: Z-Anatomy / BodyParts3D (CC BY-SA 4.0)"),
    ("x-ear", "ear, nose & throat · Ear", "Ear",
     "Ear canal skin, eardrum and middle-ear lining.",
     "Ossicles, inner ear and temporal bone: Z-Anatomy / BodyParts3D (CC BY-SA 4.0)"),
    ("x-nose", "ear, nose & throat · Nose & sinuses", "Nose and sinuses",
     "Nasal lining, turbinate surfaces and sinus air spaces.",
     "Cartilages and face bones: Z-Anatomy / BodyParts3D (CC BY-SA 4.0)"),
    ("female-fit", "body · Female · Muscles, Bones, Vessels, Nerves", "Female body: fitted layers",
     "Muscles, bones, vessels and nerves fitted from the male body to the female skin and organs. The pelvis is the "
     "reshaped male pelvis.",
     "Z-Anatomy / BodyParts3D (CC BY-SA 4.0)"),
    ("joints", "bones · Elbow, Wrist, Ankle, Neck, Skull", "Joint close-ups",
     "Where each joint is cut, which muscles, ligaments, vessels and nerves are kept, and the cut faces.",
     "Z-Anatomy / BodyParts3D (CC BY-SA 4.0)"),
    ("vh-sections", "body · Explore · Cross-section", "Real body sections",
     "Blue gel removed, image flipped to the CT view (front at the top, seen from below), depth matched to the model.",
     "Visible Human Project male cryosections, US National Library of Medicine"),
    ("names-in", "Display settings · Language · తెలుగు or हिन्दी, then tap any part", "Telugu and Hindi names",
     "The everyday Telugu and Hindi word shown under each part's English name (about 130 words, in body.html LN).",
     "Written by Urban Health"),
    ("cells", "any close-up · Cells and markers", "Cells and markers",
     "Which atlas table each close-up uses and how its parts are matched to the table's structures.",
     "HuBMAP ASCT+B tables (CC BY 4.0)"),
]
BY_ID = {i[0]: i for i in ITEMS}


def _store(db: Session) -> Setting:
    s = db.get(Setting, KEY)
    if not s:
        s = Setting(key=KEY, value={})
        db.add(s)
    return s


def _row(i, v: dict) -> dict:
    return {"id": i[0], "where": i[1], "title": i[2], "built": i[3], "basis": i[4],
            "state": v.get("state", "pending"), "at": v.get("at"), "by": v.get("by", ""), "notes": v.get("notes", [])}


@r.get("/review")
def public_review(db: Session = Depends(get_db)):
    """What a close-up shows under its source line. State and date only."""
    s = db.get(Setting, KEY)
    v = (s.value if s else None) or {}
    return {"items": {k: {"state": (v.get(k) or {}).get("state", "pending"), "at": (v.get(k) or {}).get("at")}
                      for k in BY_ID}}


@xr.get("")
def queue(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = db.get(Setting, KEY)
    v = (s.value if s else None) or {}
    items = [_row(i, v.get(i[0]) or {}) for i in ITEMS]
    order = {"changes": 0, "pending": 1, "approved": 2}
    items.sort(key=lambda x: order[x["state"]])
    return {"items": items, "open": sum(1 for x in items if x["state"] != "approved")}


class ReviewIn(BaseModel):
    state: str = Field(..., pattern="^(pending|approved|changes)$")
    note: str = Field("", max_length=2000)


@xr.post("/{iid}")
def review(iid: str, body: ReviewIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    i = BY_ID.get(iid)
    if not i:
        raise HTTPException(404, "No such model")
    note = body.note.strip()
    if body.state == "changes" and not note:
        raise HTTPException(422, "Say what needs to change")
    s = _store(db)
    v = dict(s.value or {})
    cur = dict(v.get(iid) or {})
    t = now()
    notes = list(cur.get("notes") or [])
    notes.append({"at": t, "by": a.email, "state": body.state, "text": note})
    v[iid] = {"state": body.state, "at": t, "by": a.email, "notes": notes[-50:]}
    s.value = v
    flag_modified(s, "value")
    log(db, a.email, "anatomy.review", f"{iid} {body.state} {note[:200]}")
    db.commit()
    return _row(i, v[iid])

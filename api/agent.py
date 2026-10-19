"""The family health agent: questions about the family's own records, and a daily insight per person.

The app sends a compact, already-structured context (profile, latest readings, flagged results, medicines, trackers) —
never the documents themselves. Answers are phrased for discussion with a doctor; nothing is diagnosed or prescribed.
Every call is counted against the household's plan; insights are cached per person per day so the same summary is not
paid for twice.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

from . import ai as AI

FOCUS = {"heart", "lungs", "liver", "kidneys", "pancreas", "thyroid", "stomach", "intestines", "brain", "spleen", "bones", "spine", "uterus", "prostate", "bladder", "breast", "skin", "eyes", "blood", "whole_body"}
ASK_CAP = {"free": 20, "family": 300, "plus": 100000}
INSIGHT_CAP = {"free": 10, "family": 200, "plus": 100000}

ASK_SYSTEM = """You are the health assistant inside TheHealthTracker, an Indian family health app. You answer questions about the
family's OWN records, which the app sends you as JSON context (profile, readings, lab results with flags and dates, medicines,
allergies, pregnancy or cycle trackers, vaccines). The person asking is a family member, not a clinician.

Rules you never break:
- Use only the context and general medical knowledge. If the context lacks what is needed, say what to record or ask the doctor.
- Never diagnose, never name a disease the person "has", never change or recommend a dose. Say "suggests", "may", "discuss with your doctor".
- Never guess or state fetal sex. Never give drug doses for children. Never tell someone to stop a prescribed medicine.
- Red flags (chest pain, breathlessness, stroke signs, BP >= 180/120, sugar < 70 or > 300, SpO2 < 92, heavy bleeding in pregnancy,
  a child under 3 months with fever): tell them to call 112 / go to emergency now, first and plainly.
- Plain English, short. Numbers with units and dates when quoting a record. 60-140 words unless the question needs a list.
- Do not mention AI vendors, model names or that you are an AI model. Refer to yourself as "the health assistant".
- Answer in the language of the question (English, Hindi or Telugu); keep medical terms in English.
Output ONLY a JSON object: {"answer": string, "sources": [short strings naming the records used, e.g. "HbA1c 6.8% · 12 Jun 2026"],
"actions": [0-3 short strings: things to record, ask or do], "urgent": boolean,
"focus": [0-3 body areas the answer is about, for the 3D body, from exactly this list: heart, lungs, liver, kidneys, pancreas, thyroid, stomach, intestines, brain, spleen, bones, spine, uterus, prostate, bladder, breast, skin, eyes, blood, whole_body],
"commands": [0-2 things the app can do for the person right now, ONLY when the answer calls for them, each {"type": one of book_lab | request_visit | add_reminder | add_reading | open, "label": button text max 28 chars, "args": object}.
  args by type — book_lab: {"tests": [test names]}; request_visit: {"kind": "visit"|"video", "why": short reason}; add_reminder: {"text": string, "days": integer days from today};
  add_reading: {"field": "bp"|"glu"|"w"|"spo2"|"hr"|"temp"}; open: {"page": one of meds, vax, preg, careplan, nearlabs, cards, appts, vault}]}"""

INSIGHT_SYSTEM = """You write a short daily insight for one person inside TheHealthTracker, an Indian family health app, from the JSON
context the app sends (profile, readings with dates, lab results with flags, medicines and adherence, trackers, vaccines).
Rules: never diagnose or name a condition the person "has"; use "suggests", "may", "discuss with your doctor". Prefer trends over
single values (compare dates). Mention what is going well first when something is. No fetal sex, no doses, no vendor or model names.
If a value is a red flag (BP >= 180/120, sugar < 70 or > 300, SpO2 < 92), say to seek care now and set urgent true.
Output ONLY JSON: {"headline": string (max 12 words), "points": [2-4 strings, each one plain sentence with numbers and dates],
"action": string (one concrete thing to do this week), "trend": "up"|"down"|"steady"|"", "urgent": boolean}"""


def _json(raw: str) -> dict:
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def ask(question: str, ctx: dict) -> dict:
    q = question.strip()[:600]
    r = AI.create(max_tokens=2000, system=ASK_SYSTEM,
                  messages=[{"role": "user", "content": f"Family context (JSON): {json.dumps(ctx, ensure_ascii=False)[:9000]}\n\nQuestion: {q}\n\nReturn the JSON now."}])
    out = _json("".join(b.text for b in r.content if getattr(b, "type", "") == "text"))
    return {"answer": str(out.get("answer", ""))[:1600], "sources": [str(x)[:120] for x in (out.get("sources") or [])][:6],
            "actions": [str(x)[:160] for x in (out.get("actions") or [])][:3], "urgent": bool(out.get("urgent")),
            "focus": [str(x) for x in (out.get("focus") or []) if str(x) in FOCUS][:3], "commands": _commands(out.get("commands"))}


COMMANDS = {"book_lab", "request_visit", "add_reminder", "add_reading", "open"}
PAGES = {"meds", "vax", "preg", "careplan", "nearlabs", "cards", "appts", "vault"}


def _commands(raw) -> list[dict]:
    out = []
    for c in (raw or [])[:6]:
        if not isinstance(c, dict) or c.get("type") not in COMMANDS:
            continue
        a = c.get("args") if isinstance(c.get("args"), dict) else {}
        t = c["type"]
        if t == "book_lab":
            a = {"tests": [str(x)[:60] for x in (a.get("tests") or []) if str(x).strip()][:6]}
            if not a["tests"]:
                continue
        elif t == "request_visit":
            a = {"kind": "video" if a.get("kind") == "video" else "visit", "why": str(a.get("why", ""))[:120]}
        elif t == "add_reminder":
            try:
                days = max(0, min(365, int(a.get("days", 7))))
            except Exception:
                days = 7
            a = {"text": str(a.get("text", ""))[:120], "days": days}
            if not a["text"]:
                continue
        elif t == "add_reading":
            if a.get("field") not in ("bp", "glu", "w", "spo2", "hr", "temp"):
                continue
            a = {"field": a["field"]}
        elif t == "open":
            if a.get("page") not in PAGES:
                continue
            a = {"page": a["page"]}
        out.append({"type": t, "label": str(c.get("label") or t.replace("_", " ").title())[:28], "args": a})
    return out[:2]


def insight(ctx: dict) -> dict:
    r = AI.create(max_tokens=1500, system=INSIGHT_SYSTEM,
                  messages=[{"role": "user", "content": f"Context (JSON): {json.dumps(ctx, ensure_ascii=False)[:9000]}\n\nReturn the JSON now."}])
    out = _json("".join(b.text for b in r.content if getattr(b, "type", "") == "text"))
    return {"headline": str(out.get("headline", ""))[:120], "points": [str(x)[:240] for x in (out.get("points") or [])][:4],
            "action": str(out.get("action", ""))[:200], "trend": out.get("trend") if out.get("trend") in ("up", "down", "steady") else "",
            "urgent": bool(out.get("urgent"))}


def ctx_key(ctx: dict) -> str:
    """Same records → same insight for the day; a new reading invalidates the cache."""
    return hashlib.sha256((json.dumps(ctx, sort_keys=True, ensure_ascii=False) + time.strftime("%Y-%m-%d")).encode()).hexdigest()[:24]


def enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))
